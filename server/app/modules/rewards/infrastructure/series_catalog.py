from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rewards.domain.entities import SeriesInfo
from app.modules.rewards.infrastructure.foreign_tables import chapters, series


class SqlSeriesCatalog:
    """Đọc và đặt cờ VIP của bảng `series` (thuộc M03) bằng khai báo nhẹ, không import ORM của M03."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, series_id: int) -> SeriesInfo | None:
        row = (
            await self._session.execute(
                select(
                    series.c.id, series.c.title_vi, series.c.visibility, series.c.owner_id, series.c.is_vip
                ).where(series.c.id == series_id)
            )
        ).first()
        if row is None:
            return None
        return SeriesInfo(row.id, row.title_vi, row.visibility == "public", row.owner_id, bool(row.is_vip))

    async def titles(self, series_ids: Sequence[int]) -> Mapping[int, str]:
        if not series_ids:
            return {}
        rows = await self._session.execute(
            select(series.c.id, series.c.title_vi).where(series.c.id.in_(list(series_ids)))
        )
        return {sid: title for sid, title in rows.all()}

    async def set_vip(self, series_id: int, is_vip: bool) -> None:
        await self._session.execute(update(series).where(series.c.id == series_id).values(is_vip=is_vip))

    async def has_trial_chapter(self, series_id: int) -> bool:
        stmt = select(exists().where(chapters.c.series_id == series_id, chapters.c.is_trial.is_(True)))
        return bool(await self._session.scalar(stmt))
