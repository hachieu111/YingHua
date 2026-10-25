from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library.domain.entities import Chapter, ChapterView
from app.modules.library.domain.errors import ChapterNumberTakenError
from app.modules.library.infrastructure.orm_models import ChapterModel, PageModel

_UNIQUE_NUMBER = "uq_chapters_series_id_number"


def chapter_entity(m: ChapterModel) -> Chapter:
    return Chapter(
        id=m.id,
        series_id=m.series_id,
        number=m.number,
        title=m.title,
        is_trial=m.is_trial,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _taken_or_raise(exc: IntegrityError) -> ChapterNumberTakenError:
    if _UNIQUE_NUMBER in str(exc.orig):
        return ChapterNumberTakenError()
    raise exc


class SqlChapterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, chapter_id: int) -> Chapter | None:
        model = await self._session.get(ChapterModel, chapter_id)
        return chapter_entity(model) if model else None

    async def add(
        self, series_id: int, number: Decimal, title: str | None, is_trial: bool, now: datetime
    ) -> Chapter:
        model = ChapterModel(
            series_id=series_id,
            number=number,
            title=title,
            is_trial=is_trial,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise _taken_or_raise(exc) from exc
        return chapter_entity(model)

    async def update(self, chapter: Chapter) -> None:
        model = await self._session.get(ChapterModel, chapter.id)
        if model is None:
            return
        model.number = chapter.number
        model.title = chapter.title
        model.is_trial = chapter.is_trial
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise _taken_or_raise(exc) from exc

    async def delete(self, chapter_id: int) -> None:
        await self._session.execute(delete(ChapterModel).where(ChapterModel.id == chapter_id))

    async def list_for_series(self, series_id: int, trial_only: bool) -> list[ChapterView]:
        page_count = (
            select(func.count())
            .where(PageModel.chapter_id == ChapterModel.id)
            .correlate(ChapterModel)
            .scalar_subquery()
        )
        stmt = select(ChapterModel, page_count.label("page_count")).where(ChapterModel.series_id == series_id)
        if trial_only:
            stmt = stmt.where(ChapterModel.is_trial.is_(True))
        rows = await self._session.execute(stmt.order_by(ChapterModel.number, ChapterModel.id))
        return [ChapterView(chapter_entity(r[0]), int(r.page_count)) for r in rows.all()]
