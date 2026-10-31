from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from typing import Any

from sqlalchemy import case, exists, func, literal, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnClause

from app.core.glosses import best_gloss
from app.modules.dictionary.domain.entities import (
    Definition,
    DictEntry,
    EntryRow,
    Example,
    HanziInfo,
    HskRow,
    SearchHit,
    SharedComponent,
    SpecializedMeaning,
    TatoebaExample,
    TermSample,
    WordOfTheDay,
)
from app.modules.dictionary.domain.pinyin import QueryKind, is_han_char, search_key
from app.modules.dictionary.infrastructure.hanzi_parsing import parse_etymology, parse_stroke_data
from app.modules.dictionary.infrastructure.orm_models import (
    DictEntryModel,
    DictExampleModel,
    HanziModel,
    HskWordModel,
    LookupEventModel,
    XianxiaEntryModel,
)

# `xmax = 0` chỉ đúng với dòng vừa INSERT (dòng được UPDATE có xmax khác 0): đếm thêm mới / cập nhật.
_INSERTED: ColumnClause[bool] = literal_column("(xmax = 0)")

# Thứ tự ưu tiên nguồn khi hiển thị: từ điển Thiên Chửu biên soạn kỹ cho chữ đơn, CVDICT cho từ ghép.
_SOURCE_ORDER = {"thienchuu": 0, "cvdict": 1}
_BRIEF_SOURCE = "cvdict"
_SAMPLE_OVERFETCH = 3  # lấy dư vì một từ có thể có nhiều mục (nhiều cách đọc) cùng khớp
_COMPOUND_MAX_CHARS = 6  # cụm đi kèm đủ ngắn để học thuộc (F08.11)
# Hành động người dùng chủ động tra từ; "decompose" và "tts" không phải việc tra nghĩa để học.
_LOOKUP_ACTIONS = ("hover", "lookup")
_TATOEBA = "tatoeba"


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _entry(m: DictEntryModel) -> DictEntry:
    definitions = tuple(
        Definition(str(item.get("src", m.source)), str(item.get("gloss", "")))
        for item in (m.meanings_vi or [])
        if item.get("gloss")
    )
    return DictEntry(
        id=m.id,
        simplified=m.simplified,
        traditional=m.traditional,
        pinyin=m.pinyin,
        pinyin_numeric=m.pinyin_numeric,
        han_viet=m.han_viet,
        definitions=definitions,
        english=tuple(str(e) for e in (m.meanings_en or [])),
        part_of_speech=m.part_of_speech,
        source=m.source,
        freq_rank=m.freq_rank,
    )


def search_text(definitions: Sequence[Definition]) -> str:
    """Nghĩa Việt gộp thành chữ thường để tìm kiếm (cột search_vi)."""
    return " | ".join(d.gloss for d in definitions).lower()


class SqlDictionaryReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_entries(self, term: str) -> list[DictEntry]:
        rows = (
            await self._session.execute(
                select(DictEntryModel, HskWordModel.pos)
                .outerjoin(HskWordModel, HskWordModel.word == DictEntryModel.simplified)
                .where(or_(DictEntryModel.simplified == term, DictEntryModel.traditional == term))
                .limit(20)
            )
        ).all()
        entries = []
        for model, hsk_pos in rows:
            entry = _entry(model)
            if entry.part_of_speech is None and hsk_pos:
                entry = replace(entry, part_of_speech=hsk_pos)
            entries.append(entry)
        # Mục khớp chữ giản thể trước, rồi theo thứ tự nguồn.
        entries.sort(key=lambda e: (e.simplified != term, _SOURCE_ORDER.get(e.source, 9), e.id))
        return entries

    async def find_entry_ids(self, words: Sequence[str]) -> dict[str, int]:
        if not words:
            return {}
        rows = await self._session.execute(
            select(DictEntryModel.simplified, func.min(DictEntryModel.id))
            .where(DictEntryModel.simplified.in_(list(set(words))))
            .group_by(DictEntryModel.simplified)
        )
        return {word: entry_id for word, entry_id in rows}

    async def get_hanzi(self, chars: Sequence[str]) -> dict[str, HanziInfo]:
        if not chars:
            return {}
        rows = (await self._session.execute(select(HanziModel).where(HanziModel.ch.in_(chars)))).scalars()
        return {
            m.ch: HanziInfo(
                ch=m.ch,
                pinyin=m.pinyin,
                han_viet=m.han_viet,
                radical=m.radical,
                stroke_count=m.stroke_count,
                decomposition=m.decomposition,
                components=tuple(m.components or ()),
                definition_en=m.definition_en,
                stroke_data=parse_stroke_data(m.stroke_data),
                etymology=parse_etymology(m.etymology),
            )
            for m in rows
        }

    async def get_hsk_levels(self, words: Sequence[str]) -> dict[str, int]:
        if not words:
            return {}
        rows = await self._session.execute(
            select(HskWordModel.word, HskWordModel.level).where(HskWordModel.word.in_(list(set(words))))
        )
        return {word: level for word, level in rows.all()}

    async def get_examples(self, entry_ids: Sequence[int]) -> dict[int, list[Example]]:
        if not entry_ids:
            return {}
        rows = (
            await self._session.execute(
                select(DictExampleModel)
                .where(DictExampleModel.entry_id.in_(entry_ids))
                # Câu có bản dịch Việt và câu ngắn lên trước.
                .order_by(
                    DictExampleModel.vi.is_(None), func.length(DictExampleModel.zh), DictExampleModel.id
                )
            )
        ).scalars()
        result: dict[int, list[Example]] = {}
        for m in rows:
            result.setdefault(m.entry_id, []).append(Example(m.zh, m.pinyin, m.vi, m.source))
        return result

    async def get_specialized(self, term: str) -> list[SpecializedMeaning]:
        rows = (
            await self._session.execute(
                select(XianxiaEntryModel.kind, XianxiaEntryModel.meanings)
                .where(XianxiaEntryModel.key == term, XianxiaEntryModel.kind.in_(("phrase", "name")))
                .limit(5)
            )
        ).all()
        return [SpecializedMeaning(kind, tuple(meanings or ())) for kind, meanings in rows if meanings]

    def _search_condition(self, query: str, kind: QueryKind) -> tuple[Any, Any]:
        """Trả (điều kiện khớp, hạng — càng nhỏ càng khớp sát)."""
        entry = DictEntryModel
        if kind is QueryKind.HAN:
            like = _escape_like(query)
            exact = or_(entry.simplified == query, entry.traditional == query)
            prefix = entry.simplified.like(f"{like}%", escape="\\")
            contains = entry.simplified.like(f"%{like}%", escape="\\")
            return or_(exact, contains), case((exact, 0), (prefix, 1), else_=2)
        key = search_key(query)
        pinyin_exact = entry.pinyin_search == key
        pinyin_prefix = entry.pinyin_search.like(f"{_escape_like(key)}%", escape="\\")
        if kind is QueryKind.PINYIN:
            return or_(pinyin_exact, pinyin_prefix), case((pinyin_exact, 0), else_=1)
        lowered = query.lower()
        vi_like = _escape_like(lowered)
        vi_match = entry.search_vi.like(f"%{vi_like}%", escape="\\")
        vi_start = entry.search_vi.like(f"{vi_like}%", escape="\\")
        if kind is QueryKind.VIETNAMESE or not key:
            return vi_match, case((vi_start, 2), else_=3)
        # Chữ Latin không dấu: có thể là pinyin hoặc tiếng Việt — gộp cả hai.
        return (
            or_(pinyin_exact, pinyin_prefix, vi_match),
            case((pinyin_exact, 0), (pinyin_prefix, 1), (vi_start, 2), else_=3),
        )

    async def search(
        self, query: str, kind: QueryKind, offset: int, limit: int
    ) -> tuple[list[SearchHit], int]:
        condition, rank = self._search_condition(query, kind)
        # Gộp cùng chữ + cùng cách đọc (khác nguồn) thành một kết quả.
        grouped = (
            select(
                DictEntryModel.simplified.label("simplified"),
                DictEntryModel.pinyin_numeric.label("pinyin_numeric"),
                func.min(rank).label("rank"),
                func.min(DictEntryModel.id).label("entry_id"),
            )
            .where(condition)
            .group_by(DictEntryModel.simplified, DictEntryModel.pinyin_numeric)
            .subquery()
        )
        total = await self._session.scalar(select(func.count()).select_from(grouped))
        page = (
            await self._session.execute(
                select(grouped.c.entry_id, HskWordModel.level)
                .outerjoin(HskWordModel, HskWordModel.word == grouped.c.simplified)
                .order_by(
                    grouped.c.rank,
                    HskWordModel.level.is_(None),
                    HskWordModel.level,
                    func.length(grouped.c.simplified),
                    grouped.c.entry_id,
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        ids = [row[0] for row in page]
        models = {
            m.id: m
            for m in (
                await self._session.execute(select(DictEntryModel).where(DictEntryModel.id.in_(ids)))
            ).scalars()
        }
        hits = []
        for entry_id, level in page:
            m = models[entry_id]
            first = next((item.get("gloss") for item in (m.meanings_vi or []) if item.get("gloss")), None)
            hits.append(SearchHit(m.id, m.simplified, m.pinyin, m.han_viet, first, level))
        return hits, int(total or 0)

    async def word_of_the_day(self, level: int, day: date) -> WordOfTheDay | None:
        # Chọn ổn định theo ngày: sắp xếp theo md5(từ + ngày) — cùng ngày, cùng cấp thì cùng từ.
        row = (
            await self._session.execute(
                select(HskWordModel.word, HskWordModel.level, DictEntryModel)
                .join(DictEntryModel, DictEntryModel.simplified == HskWordModel.word)
                .where(HskWordModel.level == level, func.char_length(HskWordModel.word) >= 2)
                .where(func.jsonb_array_length(DictEntryModel.meanings_vi) > 0)
                .order_by(func.md5(HskWordModel.word + literal(day.isoformat())))
                .limit(1)
            )
        ).first()
        if row is None:
            return None
        word, hsk_level, model = row
        entry = _entry(model)
        examples = (await self.get_examples([entry.id])).get(entry.id, [])
        han_viet = entry.han_viet
        if han_viet is None:
            hanzi = await self.get_hanzi(list(word))
            if all(hanzi.get(c) and hanzi[c].han_viet for c in word):
                han_viet = " ".join(hanzi[c].han_viet or "" for c in word)
        return WordOfTheDay(
            term=word,
            pinyin=entry.pinyin,
            han_viet=han_viet,
            meaning=entry.definitions[0].gloss if entry.definitions else "",
            hsk_level=hsk_level,
            example=next((e for e in examples if e.vi), examples[0] if examples else None),
        )

    async def sample_hsk_words(self, level: int, limit: int, exclude: Sequence[str]) -> list[TermSample]:
        stmt = (
            select(HskWordModel.word, DictEntryModel)
            .join(DictEntryModel, DictEntryModel.simplified == HskWordModel.word)
            .where(HskWordModel.level == level, func.jsonb_array_length(DictEntryModel.meanings_vi) > 0)
            .order_by(func.random())
            .limit(limit * _SAMPLE_OVERFETCH)
        )
        if exclude:
            stmt = stmt.where(HskWordModel.word.not_in(list(exclude)))
        best: dict[str, DictEntry] = {}
        for word, model in (await self._session.execute(stmt)).all():
            entry = _entry(model)
            if not entry.definitions:
                continue
            if word not in best and len(best) >= limit:
                continue
            if word not in best or _prefer(entry, best[word]):
                best[word] = entry
        return [
            TermSample(word, entry.pinyin, best_gloss(d.gloss for d in entry.definitions), level)
            for word, entry in best.items()
        ]

    async def find_compounds(self, term: str, limit: int) -> list[DictEntry]:
        pattern = f"%{_escape_like(term)}%"
        rows = await self._session.execute(
            select(DictEntryModel)
            .where(
                DictEntryModel.simplified.like(pattern, escape="\\"),
                DictEntryModel.simplified != term,
                func.char_length(DictEntryModel.simplified) <= _COMPOUND_MAX_CHARS,
                func.jsonb_array_length(DictEntryModel.meanings_vi) > 0,
            )
            .order_by(
                DictEntryModel.freq_rank.is_(None),
                DictEntryModel.freq_rank,
                func.char_length(DictEntryModel.simplified),
                DictEntryModel.id,
            )
            .limit(limit * _SAMPLE_OVERFETCH)
        )
        best: dict[str, DictEntry] = {}
        for model in rows.scalars():
            entry = _entry(model)
            if entry.simplified not in best and len(best) >= limit:
                continue
            if entry.simplified not in best or _prefer(entry, best[entry.simplified]):
                best[entry.simplified] = entry
        return list(best.values())

    async def brief_entries(self, terms: Sequence[str]) -> dict[str, DictEntry]:
        if not terms:
            return {}
        rows = await self._session.execute(
            select(DictEntryModel).where(DictEntryModel.simplified.in_(list(set(terms))))
        )
        best: dict[str, DictEntry] = {}
        for model in rows.scalars():
            entry = _entry(model)
            if entry.definitions and (entry.simplified not in best or _prefer(entry, best[entry.simplified])):
                best[entry.simplified] = entry
        return best

    async def find_tatoeba_examples(self, term: str, max_difficulty: int, limit: int) -> list[TatoebaExample]:
        rows = await self._session.execute(
            select(DictExampleModel)
            .join(DictEntryModel, DictEntryModel.id == DictExampleModel.entry_id)
            .where(
                DictEntryModel.simplified == term,
                DictExampleModel.source == _TATOEBA,
                DictExampleModel.difficulty_level.is_not(None),
                DictExampleModel.difficulty_level <= max_difficulty,
            )
            .order_by(DictExampleModel.id)
            .limit(limit)
        )
        return [_tatoeba(m) for m in rows.scalars()]

    async def get_tatoeba_examples(self, example_ids: Sequence[int]) -> dict[int, TatoebaExample]:
        if not example_ids:
            return {}
        rows = await self._session.execute(
            select(DictExampleModel).where(DictExampleModel.id.in_(list(example_ids)))
        )
        return {m.id: _tatoeba(m) for m in rows.scalars()}

    async def sample_translations(self, difficulty: int, exclude_ids: Sequence[int], limit: int) -> list[str]:
        stmt = (
            select(DictExampleModel.vi)
            .where(
                DictExampleModel.source == _TATOEBA,
                DictExampleModel.difficulty_level == difficulty,
                DictExampleModel.vi.is_not(None),
            )
            .order_by(func.random())
            .limit(limit)
        )
        if exclude_ids:
            stmt = stmt.where(DictExampleModel.id.not_in(list(exclude_ids)))
        return [vi for vi in (await self._session.execute(stmt)).scalars() if vi]

    async def terms_with_examples(self, terms: Sequence[str], max_difficulty: int) -> set[str]:
        if not terms:
            return set()
        rows = await self._session.execute(
            select(DictEntryModel.simplified)
            .join(DictExampleModel, DictExampleModel.entry_id == DictEntryModel.id)
            .where(
                DictEntryModel.simplified.in_(list(set(terms))),
                DictExampleModel.source == _TATOEBA,
                DictExampleModel.difficulty_level.is_not(None),
                DictExampleModel.difficulty_level <= max_difficulty,
            )
            .distinct()
        )
        return set(rows.scalars())

    async def hsk_words_containing(
        self, chars: Sequence[str], max_level: int, limit: int
    ) -> list[tuple[str, int]]:
        han = [c for c in dict.fromkeys(chars) if is_han_char(c)]
        if not han:
            return []
        # Chữ Hán không có ký tự đặc biệt của biểu thức chính quy nên ghép vào lớp ký tự là an toàn.
        pattern = "[" + "".join(han) + "]"
        rows = await self._session.execute(
            select(HskWordModel.word, HskWordModel.level)
            .where(HskWordModel.word.op("~")(pattern), HskWordModel.level <= max_level)
            .order_by(func.random())
            .limit(limit)
        )
        return [(word, level) for word, level in rows.all()]

    async def chars_sharing_components(self, chars: Sequence[str], limit: int) -> list[SharedComponent]:
        sources = (
            await self._session.execute(
                select(HanziModel.ch, HanziModel.radical, HanziModel.components).where(
                    HanziModel.ch.in_(list(set(chars)))
                )
            )
        ).all()
        parts: dict[str, set[str]] = {
            ch: {p for p in [radical, *(components or [])] if p and p != ch}
            for ch, radical, components in sources
        }
        wanted = sorted({p for ps in parts.values() for p in ps})
        if not wanted:
            return []
        rows = (
            await self._session.execute(
                select(HanziModel.ch, HanziModel.radical, HanziModel.components)
                .where(
                    or_(HanziModel.radical.in_(wanted), HanziModel.components.overlap(wanted)),
                    HanziModel.ch.not_in(list(parts)),
                )
                .order_by(func.random())
                .limit(limit)
            )
        ).all()
        result: list[SharedComponent] = []
        for ch, radical, components in rows:
            mine = {p for p in [radical, *(components or [])] if p}
            for via, via_parts in parts.items():
                shared = sorted(mine & via_parts)
                if shared:
                    result.append(SharedComponent(ch, via, shared[0]))
                    break
        return result


def _tatoeba(m: DictExampleModel) -> TatoebaExample:
    return TatoebaExample(m.id, m.zh, m.pinyin, m.vi, m.difficulty_level)


def _prefer(candidate: DictEntry, current: DictEntry) -> bool:
    """CVDICT có nghĩa ngắn gọn nên được ưu tiên làm nghĩa tiêu biểu; cùng nguồn thì mục có mã nhỏ hơn."""
    return (candidate.source != _BRIEF_SOURCE, candidate.id) < (current.source != _BRIEF_SOURCE, current.id)


class SqlDictionaryWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_entries(self, rows: Sequence[EntryRow]) -> tuple[int, int, int]:
        if not rows:
            return 0, 0, 0
        values = [
            {
                "simplified": r.simplified,
                "traditional": r.traditional,
                "pinyin": r.pinyin,
                "pinyin_numeric": r.pinyin_numeric,
                "pinyin_search": search_key(r.pinyin_numeric)[:128],
                "pinyin_source": "dict",
                "han_viet": r.han_viet,
                "meanings_vi": [{"src": d.source, "gloss": d.gloss} for d in r.definitions],
                "meanings_en": list(r.english),
                "search_vi": search_text(r.definitions),
                "part_of_speech": r.part_of_speech,
                "source": r.source,
            }
            for r in rows
        ]
        stmt = insert(DictEntryModel).values(values)
        excluded = stmt.excluded
        changed = or_(
            DictEntryModel.traditional.is_distinct_from(excluded.traditional),
            DictEntryModel.pinyin.is_distinct_from(excluded.pinyin),
            DictEntryModel.han_viet.is_distinct_from(excluded.han_viet),
            DictEntryModel.meanings_vi.is_distinct_from(excluded.meanings_vi),
            DictEntryModel.meanings_en.is_distinct_from(excluded.meanings_en),
            DictEntryModel.part_of_speech.is_distinct_from(excluded.part_of_speech),
        )
        upsert = stmt.on_conflict_do_update(
            index_elements=["simplified", "pinyin_numeric", "source"],
            set_={
                "traditional": excluded.traditional,
                "pinyin": excluded.pinyin,
                "pinyin_search": excluded.pinyin_search,
                "han_viet": excluded.han_viet,
                "meanings_vi": excluded.meanings_vi,
                "meanings_en": excluded.meanings_en,
                "search_vi": excluded.search_vi,
                "part_of_speech": excluded.part_of_speech,
            },
            where=changed,
        ).returning(_INSERTED)
        result = (await self._session.execute(upsert)).scalars().all()
        added = sum(1 for inserted in result if inserted)
        updated = len(result) - added
        return added, updated, len(rows) - len(result)

    async def upsert_hsk_words(self, rows: Sequence[HskRow]) -> tuple[int, int, int]:
        if not rows:
            return 0, 0, 0
        stmt = insert(HskWordModel).values(
            [{"word": r.word, "level": r.level, "pinyin": r.pinyin, "pos": r.pos} for r in rows]
        )
        excluded = stmt.excluded
        changed = or_(
            HskWordModel.level.is_distinct_from(excluded.level),
            HskWordModel.pinyin.is_distinct_from(excluded.pinyin),
            HskWordModel.pos.is_distinct_from(excluded.pos),
        )
        upsert = stmt.on_conflict_do_update(
            index_elements=["word"],
            set_={"level": excluded.level, "pinyin": excluded.pinyin, "pos": excluded.pos},
            where=changed,
        ).returning(_INSERTED)
        result = (await self._session.execute(upsert)).scalars().all()
        added = sum(1 for inserted in result if inserted)
        return added, len(result) - added, len(rows) - len(result)


class SqlLookupEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, user_id: int, term: str, entry_id: int | None, action: str, bubble_id: int | None = None
    ) -> bool:
        is_new_bubble = bubble_id is not None and not await self._session.scalar(
            select(
                exists().where(
                    LookupEventModel.user_id == user_id,
                    LookupEventModel.bubble_id == bubble_id,
                    LookupEventModel.action.in_(_LOOKUP_ACTIONS),
                )
            )
        )
        self._session.add(
            LookupEventModel(
                user_id=user_id, term=term[:64], entry_id=entry_id, action=action, bubble_id=bubble_id
            )
        )
        await self._session.flush()
        return is_new_bubble

    async def recent_terms(self, user_id: int, limit: int) -> list[str]:
        rows = await self._session.execute(
            select(LookupEventModel.term)
            .where(LookupEventModel.user_id == user_id, LookupEventModel.action.in_(_LOOKUP_ACTIONS))
            .group_by(LookupEventModel.term)
            .order_by(func.max(LookupEventModel.created_at).desc())
            .limit(limit)
        )
        return list(rows.scalars())

    async def count_by_term(self, user_id: int, terms: Sequence[str]) -> dict[str, int]:
        if not terms:
            return {}
        rows = await self._session.execute(
            select(LookupEventModel.term, func.count(LookupEventModel.id))
            .where(
                LookupEventModel.user_id == user_id,
                LookupEventModel.action.in_(_LOOKUP_ACTIONS),
                LookupEventModel.term.in_(list(set(terms))),
            )
            .group_by(LookupEventModel.term)
        )
        return {term: int(count) for term, count in rows.all()}
