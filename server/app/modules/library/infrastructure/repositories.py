"""Repository thư viện cá nhân (F03.13) và chấm sao (F03.14)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library.domain.entities import RatingSummary
from app.modules.library.infrastructure.orm_models import LibraryItemModel, SeriesRatingModel


class SqlLibraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: int, series_id: int, now: datetime) -> None:
        stmt = (
            insert(LibraryItemModel)
            .values(user_id=user_id, series_id=series_id, added_at=now)
            .on_conflict_do_nothing(index_elements=["user_id", "series_id"])
        )
        await self._session.execute(stmt)

    async def remove(self, user_id: int, series_id: int) -> None:
        await self._session.execute(
            delete(LibraryItemModel).where(
                LibraryItemModel.user_id == user_id, LibraryItemModel.series_id == series_id
            )
        )

    async def set_favorite(self, user_id: int, series_id: int, value: bool, now: datetime) -> None:
        stmt = (
            insert(LibraryItemModel)
            .values(user_id=user_id, series_id=series_id, is_favorite=value, added_at=now)
            .on_conflict_do_update(index_elements=["user_id", "series_id"], set_={"is_favorite": value})
        )
        await self._session.execute(stmt)


class SqlRatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, user_id: int, series_id: int, stars: int, now: datetime) -> None:
        stmt = (
            insert(SeriesRatingModel)
            .values(user_id=user_id, series_id=series_id, stars=stars, created_at=now, updated_at=now)
            .on_conflict_do_update(
                index_elements=["user_id", "series_id"], set_={"stars": stars, "updated_at": now}
            )
        )
        await self._session.execute(stmt)

    async def get(self, user_id: int, series_id: int) -> int | None:
        stars = await self._session.scalar(
            select(SeriesRatingModel.stars).where(
                SeriesRatingModel.user_id == user_id, SeriesRatingModel.series_id == series_id
            )
        )
        return int(stars) if stars is not None else None

    async def summary(self, series_id: int) -> RatingSummary:
        row = (
            await self._session.execute(
                select(func.avg(SeriesRatingModel.stars), func.count()).where(
                    SeriesRatingModel.series_id == series_id
                )
            )
        ).one()
        average = round(float(row[0]), 2) if row[0] is not None else None
        return RatingSummary(average, int(row[1]))
