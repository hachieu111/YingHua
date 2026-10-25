"""Ứng viên từ mở rộng cho bài kiểm tra (F09.09, US-NH-69).

Ghép dữ liệu của nhiều module qua giao diện công khai của từng module (không đọc bảng của module khác):
M06 (từ HSK, bảng chữ Hán, lịch sử tra, câu ví dụ), M03 (trang đã đọc), M04 (từ đã tách của bong bóng),
M07 (sổ tay) và M10 (từ gợi ý đã bỏ qua). Mỗi ứng viên gắn với ít nhất một từ đã lưu làm cầu nối.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.common_chars import is_common_char
from app.core.glosses import best_gloss
from app.modules.dictionary.application.public import resolve_hsk
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from app.modules.imaging.infrastructure.public import SqlBubbleRepository
from app.modules.library.infrastructure.public import SqlReadPagesSource
from app.modules.quiz.domain.entities import QuizWord, RelatedCandidate, RelatedLink, RelatedSource
from app.modules.quiz.domain.examples import example_difficulty_cap
from app.modules.quiz.domain.related import is_dictionary_backed, max_level_for
from app.modules.quiz.domain.rules import option_meaning
from app.modules.suggestions.infrastructure.public import SqlDismissedRepository
from app.modules.vocab.infrastructure.public import SqlVocabQuizSource

logger = logging.getLogger(__name__)

SOURCE_LIMIT = 150  # số từ tối đa lấy từ mỗi nguồn
COMPONENT_CHAR_LIMIT = 60
READ_PAGES_LIMIT = 30
RECENT_LOOKUPS_LIMIT = 60
LOOKUP_LABEL = "phần tra từ điển"
MAX_TERM_CHARS = 32


def _is_han(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


@dataclass(slots=True)
class _Pool:
    """Gom liên kết theo từ trước khi lọc."""

    links: dict[str, list[RelatedLink]] = field(default_factory=dict)
    levels: dict[str, int] = field(default_factory=dict)  # cấp HSK đã biết từ danh sách

    def add(self, term: str, link: RelatedLink, level: int | None = None) -> None:
        if not term or len(term) > MAX_TERM_CHARS or not all(_is_han(c) for c in term):
            return
        self.links.setdefault(term, []).append(link)
        if level is not None:
            self.levels[term] = level


def _link(source: RelatedSource, bridge: QuizWord, detail: str | None = None) -> RelatedLink:
    return RelatedLink(source, bridge.entry_id, bridge.term, bridge.meaning_vi, detail)


class RelatedCandidateAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def candidates(
        self, user_id: int, saved: Sequence[QuizWord], learner_level: int | None
    ) -> list[RelatedCandidate]:
        if not saved:
            return []
        pool = _Pool()
        cap = max(max_level_for(learner_level, w.hsk_level) for w in saved)
        async with SqlDictionaryUnitOfWork(self._session_factory) as dic:
            # Cầu nối chữ chung/thành phần/cùng cấp phải có trong từ điển; từ rác do OCR lưu nhầm bị loại.
            bridges = await _dictionary_backed(dic, saved)
            await self._shared_chars(dic, pool, bridges, cap)
            await self._shared_components(dic, pool, bridges, cap)
            await self._same_level(dic, pool, bridges)
            lookups = await dic.events.recent_terms(user_id, RECENT_LOOKUPS_LIMIT)
        anchors = bridges or list(saved)  # "đã gặp" không nhắc từ cầu nối trong gợi ý nên dùng tạm được
        for term in lookups:
            pool.add(term, _link(RelatedSource.ENCOUNTERED, _bridge_for(term, anchors), LOOKUP_LABEL))
        await self._encountered(user_id, pool, anchors)
        return await self._finalize(user_id, pool, saved, learner_level)

    async def _shared_chars(
        self, dic: SqlDictionaryUnitOfWork, pool: _Pool, saved: Sequence[QuizWord], cap: int
    ) -> None:
        by_char = _saved_by_char(saved)
        if not by_char:
            return
        for word, level in await dic.reader.hsk_words_containing(list(by_char), cap, SOURCE_LIMIT):
            char = next((c for c in word if c in by_char), None)
            if char is not None:
                pool.add(word, _link(RelatedSource.SHARED_CHAR, by_char[char], char), level)

    async def _shared_components(
        self, dic: SqlDictionaryUnitOfWork, pool: _Pool, saved: Sequence[QuizWord], cap: int
    ) -> None:
        by_char = _saved_by_char(saved)
        if not by_char:
            return
        shared = {
            s.related: s
            for s in await dic.reader.chars_sharing_components(list(by_char), COMPONENT_CHAR_LIMIT)
        }
        shared = {c: s for c, s in shared.items() if not is_common_char(s.component)}
        if not shared:
            return
        for word, level in await dic.reader.hsk_words_containing(list(shared), cap, SOURCE_LIMIT):
            char = next((c for c in word if c in shared), None)
            if char is not None and shared[char].via in by_char:
                link = _link(
                    RelatedSource.SHARED_COMPONENT, by_char[shared[char].via], shared[char].component
                )
                pool.add(word, link, level)

    async def _same_level(self, dic: SqlDictionaryUnitOfWork, pool: _Pool, saved: Sequence[QuizWord]) -> None:
        exclude = [w.term for w in saved]
        bridges: dict[int, QuizWord] = {}
        for w in saved:
            if w.hsk_level is not None:
                bridges.setdefault(w.hsk_level, w)
        for level, bridge in bridges.items():
            for sample in await dic.reader.sample_hsk_words(level, SOURCE_LIMIT // 10, exclude):
                pool.add(sample.term, _link(RelatedSource.SAME_LEVEL, bridge), sample.hsk_level)

    async def _encountered(self, user_id: int, pool: _Pool, saved: Sequence[QuizWord]) -> None:
        async with self._session_factory() as session:
            pages = await SqlReadPagesSource(session).recent_read_pages(user_id, READ_PAGES_LIMIT)
            bubbles = SqlBubbleRepository(session)
            cache: dict[int, list[str]] = {}
            for page in pages:
                if page.translation_id not in cache:
                    rows = await bubbles.list_by_translation(page.translation_id)
                    cache[page.translation_id] = [
                        t["word"]
                        for b in rows
                        for t in b.tokens
                        if isinstance(t, dict) and isinstance(t.get("word"), str)
                    ]
                for word in cache[page.translation_id]:
                    pool.add(
                        word, _link(RelatedSource.ENCOUNTERED, _bridge_for(word, saved), page.series_title)
                    )

    async def _finalize(
        self, user_id: int, pool: _Pool, saved: Sequence[QuizWord], learner_level: int | None
    ) -> list[RelatedCandidate]:
        terms = list(pool.links)
        bridge_level = {w.entry_id: w.hsk_level for w in saved}
        async with self._session_factory() as session:
            excluded = await SqlVocabQuizSource(session).saved_terms(user_id, terms)
            excluded |= await SqlDismissedRepository(session).terms(user_id)
        terms = [t for t in terms if t not in excluded]
        async with SqlDictionaryUnitOfWork(self._session_factory) as dic:
            levels = await self._levels(dic, terms, pool)
            kept = {t: _within_cap(pool.links[t], levels.get(t), learner_level, bridge_level) for t in terms}
            terms = [t for t in terms if kept[t]]
            briefs = await dic.reader.brief_entries(terms)
            with_examples: set[str] = set()
            for cap in {example_difficulty_cap(learner_level, levels[t]) for t in terms}:
                group = [t for t in terms if example_difficulty_cap(learner_level, levels[t]) == cap]
                with_examples |= await dic.reader.terms_with_examples(group, cap)
        result = []
        for term in terms:
            entry = briefs.get(term)
            meaning = option_meaning(best_gloss(d.gloss for d in entry.definitions)) if entry else ""
            if entry is None or not meaning or term not in with_examples:
                continue
            result.append(
                RelatedCandidate(term, entry.pinyin, meaning, levels[term], tuple(kept[term]), entry.han_viet)
            )
        return result

    async def _levels(self, dic: SqlDictionaryUnitOfWork, terms: list[str], pool: _Pool) -> dict[str, int]:
        unknown = [t for t in terms if t not in pool.levels]
        table = (
            await dic.reader.get_hsk_levels([*unknown, *{c for t in unknown for c in t}]) if unknown else {}
        )
        levels = {t: pool.levels[t] for t in terms if t in pool.levels}
        for term in unknown:
            level = resolve_hsk(term, table).level
            if level is not None:
                levels[term] = level
        return levels  # từ không xác định được cấp HSK bị loại vì không so được với giới hạn


def _within_cap(
    links: list[RelatedLink],
    level: int | None,
    learner_level: int | None,
    bridge_level: dict[int, int | None],
) -> list[RelatedLink]:
    if level is None:
        return []
    return [
        link
        for link in links
        if level <= max_level_for(learner_level, bridge_level.get(link.bridge_entry_id))
    ]


def _saved_by_char(saved: Sequence[QuizWord]) -> dict[str, QuizWord]:
    by_char: dict[str, QuizWord] = {}
    for w in saved:
        for c in w.term:
            if _is_han(c) and not is_common_char(c):
                by_char.setdefault(c, w)
    return by_char


def _bridge_for(term: str, saved: Sequence[QuizWord]) -> QuizWord:
    """Từ đã lưu làm cầu nối cho từ đã gặp: ưu tiên từ có chung chữ, không thì từ đầu tiên."""
    by_char = _saved_by_char(saved)
    return next((by_char[c] for c in term if c in by_char), saved[0])


async def _dictionary_backed(dic: SqlDictionaryUnitOfWork, saved: Sequence[QuizWord]) -> list[QuizWord]:
    """Từ đã lưu có cấp HSK hoặc có nghĩa trong từ điển M06."""
    briefs = await dic.reader.brief_entries([w.term for w in saved])
    result: list[QuizWord] = []
    for word in saved:
        entry = briefs.get(word.term)
        gloss = best_gloss(d.gloss for d in entry.definitions) if entry else None
        if is_dictionary_backed(word.hsk_level, gloss):
            result.append(word)
    return result
