from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reader.domain.entities import (
    Annotation,
    AnnotationInput,
    BookmarkRef,
    ConsumeOutcome,
    Stroke,
)
from app.modules.reader.infrastructure.orm_models import (
    BubbleEditModel,
    GuestSessionModel,
    PageAnnotationModel,
)


def _highlights(raw: Any) -> dict[int, str]:
    """Cột JSONB mặc định là `[]` (lúc chỉ có dấu trang); chỉ dạng từ điển mới là tô màu thật."""
    if not isinstance(raw, dict):
        return {}
    return {int(k): str(v) for k, v in raw.items() if str(k).isdigit()}


def _strokes(raw: Any) -> tuple[Stroke, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        Stroke(color=str(s["color"]), points=tuple((float(p["x"]), float(p["y"])) for p in s["points"]))
        for s in raw
    )


def _annotation(m: PageAnnotationModel) -> Annotation:
    return Annotation(
        user_id=m.user_id,
        page_id=m.page_id,
        is_bookmarked=m.is_bookmarked,
        highlights=_highlights(m.highlights),
        strokes=_strokes(m.strokes),
        updated_at=m.updated_at,
    )


def _highlights_json(highlights: dict[int, str]) -> dict[str, str]:
    return {str(k): v for k, v in highlights.items()}


def _strokes_json(strokes: Sequence[Stroke]) -> list[dict[str, Any]]:
    return [{"color": s.color, "points": [{"x": x, "y": y} for x, y in s.points]} for s in strokes]


class SqlBubbleEditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_many(self, user_id: int, bubble_ids: Sequence[int]) -> dict[int, str]:
        if not bubble_ids:
            return {}
        rows = await self._session.execute(
            select(BubbleEditModel.bubble_id, BubbleEditModel.text_vi).where(
                BubbleEditModel.user_id == user_id, BubbleEditModel.bubble_id.in_(list(bubble_ids))
            )
        )
        return {bubble_id: text for bubble_id, text in rows.all()}

    async def upsert(self, user_id: int, bubble_id: int, text_vi: str, now: datetime) -> None:
        stmt = insert(BubbleEditModel).values(
            user_id=user_id, bubble_id=bubble_id, text_vi=text_vi, created_at=now, updated_at=now
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=[BubbleEditModel.user_id, BubbleEditModel.bubble_id],
                set_={"text_vi": text_vi, "updated_at": now},
            )
        )

    async def delete(self, user_id: int, bubble_id: int) -> bool:
        rows = await self._session.execute(
            delete(BubbleEditModel)
            .where(BubbleEditModel.user_id == user_id, BubbleEditModel.bubble_id == bubble_id)
            .returning(BubbleEditModel.bubble_id)
        )
        return rows.scalar_one_or_none() is not None


class SqlAnnotationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _row(self, user_id: int, page_id: int) -> PageAnnotationModel | None:
        return await self._session.get(PageAnnotationModel, (user_id, page_id))

    async def get(self, user_id: int, page_id: int) -> Annotation | None:
        model = await self._row(user_id, page_id)
        return _annotation(model) if model else None

    async def set_bookmark(self, user_id: int, page_id: int, value: bool, now: datetime) -> Annotation:
        stmt = insert(PageAnnotationModel).values(
            user_id=user_id,
            page_id=page_id,
            is_bookmarked=value,
            highlights={},
            strokes=[],
            updated_at=now,
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=[PageAnnotationModel.user_id, PageAnnotationModel.page_id],
                set_={"is_bookmarked": value, "updated_at": now},
            )
        )
        await self._session.flush()
        self._session.expire_all()
        model = await self._row(user_id, page_id)
        assert model is not None
        return _annotation(model)

    async def save(self, user_id: int, page_id: int, data: AnnotationInput, now: datetime) -> Annotation:
        highlights, strokes = _highlights_json(data.highlights), _strokes_json(data.strokes)
        stmt = insert(PageAnnotationModel).values(
            user_id=user_id,
            page_id=page_id,
            is_bookmarked=False,
            highlights=highlights,
            strokes=strokes,
            updated_at=now,
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=[PageAnnotationModel.user_id, PageAnnotationModel.page_id],
                set_={"highlights": highlights, "strokes": strokes, "updated_at": now},
            )
        )
        await self._session.flush()
        self._session.expire_all()
        model = await self._row(user_id, page_id)
        assert model is not None
        return _annotation(model)

    async def clear(self, user_id: int, page_id: int, now: datetime) -> None:
        await self._session.execute(
            update(PageAnnotationModel)
            .where(PageAnnotationModel.user_id == user_id, PageAnnotationModel.page_id == page_id)
            .values(highlights={}, strokes=[], updated_at=now)
        )
        await self._session.execute(
            delete(PageAnnotationModel).where(
                PageAnnotationModel.user_id == user_id,
                PageAnnotationModel.page_id == page_id,
                PageAnnotationModel.is_bookmarked.is_(False),
            )
        )

    async def list_bookmarked(self, user_id: int, offset: int, limit: int) -> tuple[list[BookmarkRef], int]:
        conditions = (PageAnnotationModel.user_id == user_id, PageAnnotationModel.is_bookmarked.is_(True))
        total = await self._session.scalar(
            select(func.count()).select_from(PageAnnotationModel).where(*conditions)
        )
        rows = await self._session.execute(
            select(PageAnnotationModel.page_id, PageAnnotationModel.updated_at)
            .where(*conditions)
            .order_by(PageAnnotationModel.updated_at.desc(), PageAnnotationModel.page_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [BookmarkRef(page_id, at) for page_id, at in rows.all()], int(total or 0)


class SqlGuestSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def consume(self, session_id: uuid.UUID, limit: int, now: datetime) -> tuple[ConsumeOutcome, int]:
        updated = await self._session.execute(
            update(GuestSessionModel)
            .where(
                GuestSessionModel.id == session_id,
                GuestSessionModel.expires_at > now,
                GuestSessionModel.lookup_count < limit,
            )
            .values(lookup_count=GuestSessionModel.lookup_count + 1)
            .returning(GuestSessionModel.lookup_count)
        )
        used = updated.scalar_one_or_none()
        if used is not None:
            return ConsumeOutcome.OK, int(used)
        current = await self._session.execute(
            select(GuestSessionModel.lookup_count).where(
                GuestSessionModel.id == session_id, GuestSessionModel.expires_at > now
            )
        )
        count = current.scalar_one_or_none()
        if count is None:
            return ConsumeOutcome.UNKNOWN, 0
        return ConsumeOutcome.LIMIT_REACHED, int(count)

    async def create(self, now: datetime, expires_at: datetime, used: int) -> uuid.UUID:
        session_id = uuid.uuid4()
        self._session.add(
            GuestSessionModel(id=session_id, lookup_count=used, created_at=now, expires_at=expires_at)
        )
        await self._session.flush()
        return session_id

    async def delete_expired(self, now: datetime) -> int:
        rows = await self._session.execute(
            delete(GuestSessionModel)
            .where(GuestSessionModel.expires_at <= now)
            .returning(GuestSessionModel.id)
        )
        return len(rows.all())
