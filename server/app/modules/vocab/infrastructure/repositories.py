from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ColumnElement,
    DateTime,
    column,
    delete,
    exists,
    func,
    or_,
    select,
    table,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import escape_like
from app.modules.vocab.domain.entities import (
    ContextSummary,
    NewVocabContext,
    NewVocabEntry,
    VocabContext,
    VocabEntry,
    VocabFilter,
    VocabOrigin,
    VocabStatus,
)
from app.modules.vocab.infrastructure.orm_models import VocabContextModel, VocabEntryModel

# Tham chiếu chỉ-đọc tới bảng thẻ của M08 (hợp đồng lược đồ) để lọc "đến hạn" ngay trong SQL,
# không import ORM nội bộ của M08.
_CARDS = table(
    "cards",
    column("user_id", BigInteger),
    column("vocab_entry_id", BigInteger),
    column("is_suspended", Boolean),
    column("due_at", DateTime(timezone=True)),
)


def _entry(m: VocabEntryModel) -> VocabEntry:
    return VocabEntry(
        id=m.id,
        user_id=m.user_id,
        term=m.term,
        status=VocabStatus(m.status),
        origin=VocabOrigin(m.source),
        hsk_source=m.hsk_source,
        created_at=m.created_at,
        updated_at=m.updated_at,
        entry_id=m.entry_id,
        pinyin=m.pinyin,
        meaning_vi=m.meaning_vi,
        hsk_level=m.hsk_level,
        note=m.note,
        is_starred=m.is_starred,
    )


def _context(m: VocabContextModel) -> VocabContext:
    return VocabContext(
        id=m.id,
        vocab_entry_id=m.vocab_entry_id,
        sentence_zh=m.sentence_zh,
        created_at=m.created_at,
        bubble_id=m.bubble_id,
        page_id=m.page_id,
        sentence_vi=m.sentence_vi,
        snippet_file_id=m.snippet_file_id,
        source_label=m.source_label,
    )


def _conditions(flt: VocabFilter) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [VocabEntryModel.user_id == flt.user_id]
    if flt.status is not None:
        conditions.append(VocabEntryModel.status == flt.status.value)
    if flt.hsk_level is not None:
        conditions.append(VocabEntryModel.hsk_level == flt.hsk_level)
    if flt.hsk_none:
        conditions.append(VocabEntryModel.hsk_level.is_(None))
    if flt.starred is not None:
        conditions.append(VocabEntryModel.is_starred.is_(flt.starred))
    if flt.query:
        pattern = f"%{escape_like(flt.query)}%"
        conditions.append(
            or_(
                VocabEntryModel.term.ilike(pattern, escape="\\"),
                VocabEntryModel.pinyin.ilike(pattern, escape="\\"),
                VocabEntryModel.meaning_vi.ilike(pattern, escape="\\"),
            )
        )
    if flt.page_ids is not None:
        in_series = exists().where(
            VocabContextModel.vocab_entry_id == VocabEntryModel.id,
            VocabContextModel.page_id.in_(list(flt.page_ids)),
        )
        conditions.append(in_series)
    if flt.due is not None and flt.now is not None:
        has_due_card = exists().where(
            _CARDS.c.user_id == flt.user_id,
            _CARDS.c.vocab_entry_id == VocabEntryModel.id,
            _CARDS.c.is_suspended.is_(False),
            _CARDS.c.due_at <= flt.now,
        )
        is_due = (VocabEntryModel.status == VocabStatus.LEARNING.value) & has_due_card
        conditions.append(is_due if flt.due else ~is_due)
    return conditions


class SqlVocabRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int, entry_id: int) -> VocabEntry | None:
        model = (
            await self._session.execute(
                select(VocabEntryModel).where(
                    VocabEntryModel.id == entry_id, VocabEntryModel.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        return _entry(model) if model else None

    async def get_many(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, VocabEntry]:
        if not entry_ids:
            return {}
        rows = await self._session.execute(
            select(VocabEntryModel).where(
                VocabEntryModel.user_id == user_id, VocabEntryModel.id.in_(list(entry_ids))
            )
        )
        return {m.id: _entry(m) for m in rows.scalars()}

    async def get_by_term(self, user_id: int, term: str) -> VocabEntry | None:
        model = (
            await self._session.execute(
                select(VocabEntryModel).where(
                    VocabEntryModel.user_id == user_id, VocabEntryModel.term == term
                )
            )
        ).scalar_one_or_none()
        return _entry(model) if model else None

    async def add_if_absent(self, new_entry: NewVocabEntry) -> VocabEntry | None:
        stmt = (
            insert(VocabEntryModel)
            .values(
                user_id=new_entry.user_id,
                term=new_entry.term,
                entry_id=new_entry.entry_id,
                pinyin=new_entry.pinyin,
                meaning_vi=new_entry.meaning_vi,
                hsk_level=new_entry.hsk_level,
                hsk_source=new_entry.hsk_source,
                status=VocabStatus.LEARNING.value,
                source=new_entry.origin.value,
                is_starred=False,
                created_at=new_entry.created_at,
                updated_at=new_entry.created_at,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "term"])
            .returning(VocabEntryModel)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _entry(model) if model else None

    async def update(self, entry: VocabEntry) -> None:
        await self._session.execute(
            update(VocabEntryModel)
            .where(VocabEntryModel.id == entry.id, VocabEntryModel.user_id == entry.user_id)
            .values(
                status=entry.status.value,
                note=entry.note,
                meaning_vi=entry.meaning_vi,
                is_starred=entry.is_starred,
                updated_at=entry.updated_at,
            )
        )

    async def delete(self, user_id: int, entry_id: int) -> None:
        await self._session.execute(
            delete(VocabEntryModel).where(VocabEntryModel.id == entry_id, VocabEntryModel.user_id == user_id)
        )

    async def search(self, flt: VocabFilter, offset: int, limit: int) -> tuple[list[VocabEntry], int]:
        conditions = _conditions(flt)
        total = (
            await self._session.execute(select(func.count(VocabEntryModel.id)).where(*conditions))
        ).scalar_one()
        rows = await self._session.execute(
            select(VocabEntryModel)
            .where(*conditions)
            .order_by(VocabEntryModel.created_at.desc(), VocabEntryModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_entry(m) for m in rows.scalars()], int(total)

    async def status_counts(self, user_id: int) -> dict[str, int]:
        """Số mục từ theo trạng thái; trạng thái chưa có từ nào vẫn trả 0."""
        rows = await self._session.execute(
            select(VocabEntryModel.status, func.count(VocabEntryModel.id))
            .where(VocabEntryModel.user_id == user_id)
            .group_by(VocabEntryModel.status)
        )
        counts = {status.value: 0 for status in VocabStatus}
        counts.update({status: int(n) for status, n in rows.all()})
        return counts

    async def terms_with_context_on_page(self, user_id: int, page_id: int, terms: Sequence[str]) -> set[str]:
        if not terms:
            return set()
        rows = await self._session.execute(
            select(VocabEntryModel.term)
            .join(VocabContextModel, VocabContextModel.vocab_entry_id == VocabEntryModel.id)
            .where(
                VocabEntryModel.user_id == user_id,
                VocabContextModel.page_id == page_id,
                VocabEntryModel.term.in_(list(set(terms))),
            )
            .distinct()
        )
        return set(rows.scalars())

    async def existing_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        if not terms:
            return set()
        rows = await self._session.execute(
            select(VocabEntryModel.term).where(
                VocabEntryModel.user_id == user_id, VocabEntryModel.term.in_(list(set(terms)))
            )
        )
        return set(rows.scalars())

    async def starred_ids(self, user_id: int) -> list[int]:
        rows = await self._session.execute(
            select(VocabEntryModel.id).where(
                VocabEntryModel.user_id == user_id, VocabEntryModel.is_starred.is_(True)
            )
        )
        return list(rows.scalars())


class SqlVocabContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, new_context: NewVocabContext) -> VocabContext | None:
        values: dict[str, Any] = {
            "vocab_entry_id": new_context.vocab_entry_id,
            "bubble_id": new_context.bubble_id,
            "page_id": new_context.page_id,
            "sentence_zh": new_context.sentence_zh,
            "sentence_vi": new_context.sentence_vi,
            "snippet_file_id": new_context.snippet_file_id,
            "source_label": new_context.source_label,
            "created_at": new_context.created_at,
        }
        stmt = (
            insert(VocabContextModel)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["vocab_entry_id", "bubble_id"])
            .returning(VocabContextModel)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _context(model) if model else None

    async def has_bubble(self, vocab_entry_id: int, bubble_id: int) -> bool:
        stmt = select(
            exists().where(
                VocabContextModel.vocab_entry_id == vocab_entry_id, VocabContextModel.bubble_id == bubble_id
            )
        )
        return bool((await self._session.execute(stmt)).scalar_one())

    async def list_for_entry(self, vocab_entry_id: int) -> list[VocabContext]:
        rows = await self._session.execute(
            select(VocabContextModel)
            .where(VocabContextModel.vocab_entry_id == vocab_entry_id)
            .order_by(VocabContextModel.created_at.desc(), VocabContextModel.id.desc())
        )
        return [_context(m) for m in rows.scalars()]

    async def get(self, vocab_entry_id: int, context_id: int) -> VocabContext | None:
        model = (
            await self._session.execute(
                select(VocabContextModel).where(
                    VocabContextModel.id == context_id, VocabContextModel.vocab_entry_id == vocab_entry_id
                )
            )
        ).scalar_one_or_none()
        return _context(model) if model else None

    async def delete(self, context_id: int) -> None:
        await self._session.execute(delete(VocabContextModel).where(VocabContextModel.id == context_id))

    async def summaries(self, entry_ids: Sequence[int]) -> dict[int, ContextSummary]:
        if not entry_ids:
            return {}
        rows = await self._session.execute(
            select(VocabContextModel)
            .where(VocabContextModel.vocab_entry_id.in_(list(entry_ids)))
            .order_by(VocabContextModel.created_at.desc(), VocabContextModel.id.desc())
        )
        counts: dict[int, int] = {}
        latest: dict[int, VocabContext] = {}
        for model in rows.scalars():
            counts[model.vocab_entry_id] = counts.get(model.vocab_entry_id, 0) + 1
            latest.setdefault(model.vocab_entry_id, _context(model))
        return {i: ContextSummary(counts[i], latest[i]) for i in counts}

    async def snippet_file_ids(self, vocab_entry_id: int) -> list[int]:
        rows = await self._session.execute(
            select(VocabContextModel.snippet_file_id).where(
                VocabContextModel.vocab_entry_id == vocab_entry_id,
                VocabContextModel.snippet_file_id.is_not(None),
            )
        )
        return [file_id for file_id in rows.scalars() if file_id is not None]

    async def page_links(self, user_id: int) -> list[tuple[int, int]]:
        rows = await self._session.execute(
            select(VocabContextModel.vocab_entry_id, VocabContextModel.page_id)
            .join(VocabEntryModel, VocabEntryModel.id == VocabContextModel.vocab_entry_id)
            .where(VocabEntryModel.user_id == user_id, VocabContextModel.page_id.is_not(None))
        )
        return [(entry_id, page_id) for entry_id, page_id in rows.all() if page_id is not None]

    async def entry_ids_for_pages(self, user_id: int, page_ids: Sequence[int]) -> list[int]:
        if not page_ids:
            return []
        rows = await self._session.execute(
            select(VocabContextModel.vocab_entry_id)
            .join(VocabEntryModel, VocabEntryModel.id == VocabContextModel.vocab_entry_id)
            .where(VocabEntryModel.user_id == user_id, VocabContextModel.page_id.in_(list(page_ids)))
            .distinct()
        )
        return list(rows.scalars())
