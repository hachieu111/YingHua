from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library.domain.entities import (
    ContinueItem,
    ReadingMode,
    ReadingProgress,
    ResumePoint,
    SeriesProgress,
    Visibility,
)
from app.modules.library.infrastructure.orm_models import (
    ChapterModel,
    PageModel,
    PageReadModel,
    ReadingProgressModel,
    SeriesModel,
)
from app.modules.library.infrastructure.series_repository import series_entity


def _progress(m: ReadingProgressModel) -> ReadingProgress:
    return ReadingProgress(
        user_id=m.user_id,
        chapter_id=m.chapter_id,
        last_page_no=m.last_page_no,
        mode=ReadingMode(m.mode),
        completed=m.completed,
        updated_at=m.updated_at,
    )


def _page_id_of(progress: Any) -> Any:
    return (
        select(PageModel.id)
        .where(PageModel.chapter_id == progress.c.chapter_id, PageModel.page_no == progress.c.last_page_no)
        .scalar_subquery()
    )


def _total_pages_of(progress: Any) -> Any:
    return select(func.count()).where(PageModel.chapter_id == progress.c.chapter_id).scalar_subquery()


class SqlProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int, chapter_id: int) -> ReadingProgress | None:
        model = await self._session.get(ReadingProgressModel, (user_id, chapter_id))
        return _progress(model) if model else None

    async def upsert(
        self,
        user_id: int,
        chapter_id: int,
        page_no: int,
        mode: ReadingMode,
        completed: bool,
        now: datetime,
    ) -> ReadingProgress:
        values = {
            "user_id": user_id,
            "chapter_id": chapter_id,
            "last_page_no": page_no,
            "mode": mode.value,
            "completed": completed,
            "updated_at": now,
        }
        stmt = (
            insert(ReadingProgressModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["user_id", "chapter_id"],
                set_={k: v for k, v in values.items() if k not in ("user_id", "chapter_id")},
            )
        )
        await self._session.execute(stmt)
        return ReadingProgress(user_id, chapter_id, page_no, mode, completed, now)

    async def mark_page_read(self, user_id: int, page_id: int, now: datetime) -> None:
        stmt = (
            insert(PageReadModel)
            .values(user_id=user_id, page_id=page_id, first_read_at=now)
            .on_conflict_do_nothing(index_elements=["user_id", "page_id"])
        )
        await self._session.execute(stmt)

    def _latest_per_series(self, user_id: int, series_ids: Sequence[int] | None = None) -> Any:
        stmt = (
            select(
                ReadingProgressModel.chapter_id,
                ReadingProgressModel.last_page_no,
                ReadingProgressModel.mode,
                ReadingProgressModel.completed,
                ReadingProgressModel.updated_at,
                ChapterModel.series_id,
                ChapterModel.number,
                ChapterModel.title,
            )
            .join(ChapterModel, ChapterModel.id == ReadingProgressModel.chapter_id)
            .where(ReadingProgressModel.user_id == user_id)
        )
        if series_ids is not None:
            stmt = stmt.where(ChapterModel.series_id.in_(series_ids))
        return (
            stmt.distinct(ChapterModel.series_id)
            .order_by(ChapterModel.series_id, ReadingProgressModel.updated_at.desc())
            .subquery("latest")
        )

    async def latest_for_series(self, user_id: int, series_id: int) -> ResumePoint | None:
        latest = self._latest_per_series(user_id)
        stmt = select(
            latest, _page_id_of(latest).label("page_id"), _total_pages_of(latest).label("total")
        ).where(latest.c.series_id == series_id)
        row = (await self._session.execute(stmt)).first()
        return _resume(row) if row else None

    async def summaries_for_series(
        self, user_id: int, series_ids: Sequence[int]
    ) -> dict[int, SeriesProgress]:
        """Tiến độ theo lô cho nhiều truyện: 3 truy vấn cố định, không phụ thuộc số truyện."""
        if not series_ids:
            return {}
        latest = self._latest_per_series(user_id, series_ids)
        resume_rows = await self._session.execute(
            select(latest, _page_id_of(latest).label("page_id"), _total_pages_of(latest).label("total"))
        )
        resumes = {r.series_id: _resume(r) for r in resume_rows.all()}
        total_rows = await self._session.execute(
            select(ChapterModel.series_id, func.count(PageModel.id))
            .join(PageModel, PageModel.chapter_id == ChapterModel.id)
            .where(ChapterModel.series_id.in_(series_ids))
            .group_by(ChapterModel.series_id)
        )
        totals = {sid: int(n) for sid, n in total_rows.all()}
        read_rows = await self._session.execute(
            select(ChapterModel.series_id, func.count(PageReadModel.page_id))
            .join(PageModel, PageModel.id == PageReadModel.page_id)
            .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .where(PageReadModel.user_id == user_id, ChapterModel.series_id.in_(series_ids))
            .group_by(ChapterModel.series_id)
        )
        reads = {sid: int(n) for sid, n in read_rows.all()}
        result: dict[int, SeriesProgress] = {}
        for sid in series_ids:
            read = reads.get(sid, 0)
            resume = resumes.get(sid)
            if resume is None and read == 0:
                continue
            result[sid] = SeriesProgress(read, totals.get(sid, 0), resume)
        return result

    async def list_continue(self, user_id: int, limit: int) -> list[ContinueItem]:
        latest = self._latest_per_series(user_id)
        stmt = (
            select(
                latest,
                _page_id_of(latest).label("page_id"),
                _total_pages_of(latest).label("total"),
                SeriesModel,
            )
            .join(SeriesModel, SeriesModel.id == latest.c.series_id)
            .where(
                latest.c.completed.is_(False),
                or_(
                    SeriesModel.visibility == Visibility.PUBLIC.value,
                    and_(SeriesModel.owner_id == user_id),
                ),
            )
            .order_by(latest.c.updated_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [ContinueItem(_resume(r), series_entity(r.SeriesModel), r.title) for r in rows]

    async def move_after_page_deleted(
        self, chapter_id: int, deleted_page_no: int, new_page_no: int | None
    ) -> None:
        if new_page_no is None:
            await self._session.execute(
                delete(ReadingProgressModel).where(ReadingProgressModel.chapter_id == chapter_id)
            )
            return
        await self._session.execute(
            update(ReadingProgressModel)
            .where(
                ReadingProgressModel.chapter_id == chapter_id,
                ReadingProgressModel.last_page_no == deleted_page_no,
            )
            .values(last_page_no=new_page_no)
        )


def _resume(row: Any) -> ResumePoint:
    return ResumePoint(
        series_id=row.series_id,
        chapter_id=row.chapter_id,
        chapter_number=row.number,
        page_no=row.last_page_no,
        page_id=row.page_id,
        total_pages=int(row.total),
        mode=ReadingMode(row.mode),
        completed=row.completed,
        updated_at=row.updated_at,
    )
