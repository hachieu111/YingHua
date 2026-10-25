from __future__ import annotations

from collections.abc import Callable

from app.core.common_chars import is_stop_term
from app.core.glosses import short_meaning
from app.modules.auth.application.public import Identity
from app.modules.suggestions.application.analysis import analyze_chapter, fold_reduplicated
from app.modules.suggestions.application.dto import SuggestionList
from app.modules.suggestions.application.ports import (
    ChapterSource,
    LearnerLevelSource,
    SuggestionUnitOfWork,
    TermBrief,
    TermHints,
)
from app.modules.suggestions.domain.entities import ScoredTerm, Suggestion
from app.modules.suggestions.domain.rules import rank_terms


class ListSuggestionsUseCase:
    """F10.01 — Danh sách "Từ nên học" trong chương, tính khi yêu cầu (US-NH-51).

    Gom từ đã tách của các trang đã xong, loại từ đã có trong sổ tay (mọi trạng thái) và từ đã bỏ qua ở mọi
    chương, rồi xếp theo điểm từ tần suất, độ phù hợp HSK (chỉ khi đã khai báo trình độ) và số lần tra.
    Chương không đọc được → 404. Còn trang chưa xong → `processing` (vẫn trả gợi ý của các trang đã xong).
    """

    def __init__(
        self,
        uow_factory: Callable[[], SuggestionUnitOfWork],
        chapters: ChapterSource,
        hints: TermHints,
        levels: LearnerLevelSource,
    ) -> None:
        self._uow_factory = uow_factory
        self._chapters = chapters
        self._hints = hints
        self._levels = levels

    async def execute(self, identity: Identity, chapter_id: int, limit: int) -> SuggestionList:
        user_id = identity.user_id
        learner_level = await self._levels.hsk_level_of(user_id)
        async with self._uow_factory() as uow:
            analysis = await analyze_chapter(self._chapters, uow, identity, chapter_id)
            folded = await fold_reduplicated(analysis.stats, self._hints)
            candidates = {t: s for t, s in folded.items() if not is_stop_term(t)}
            excluded = await uow.saved.saved_terms(user_id, list(candidates)) | await uow.dismissed.terms(
                user_id
            )
            stats = {t: s for t, s in candidates.items() if t not in excluded}
            lookups = await uow.lookups.count_by_term(user_id, list(stats))
        levels = await self._hints.hsk_levels(list(stats))
        top = rank_terms(stats, lookups, levels, learner_level)[:limit]
        briefs = await self._hints.briefs([t.stats.term for t in top])
        return SuggestionList(analysis.status, learner_level, [_suggestion(t, briefs) for t in top])


def _suggestion(scored: ScoredTerm, briefs: dict[str, TermBrief]) -> Suggestion:
    s = scored.stats
    brief = briefs.get(s.term)
    pinyin = s.pinyin or (brief.pinyin if brief else None)
    meaning = short_meaning(brief.meaning_vi if brief else None) or None
    return Suggestion(
        term=s.term,
        pinyin=pinyin,
        meaning_vi=meaning,
        hsk_level=scored.hsk_level,
        occurrences=s.occurrences,
        lookups=scored.lookups,
        score=scored.score,
        bubble_id=s.bubble_id,
        page_id=s.page_id,
        page_no=s.page_no,
    )
