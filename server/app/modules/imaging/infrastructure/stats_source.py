"""Số liệu xử lý ảnh (M04) cho thống kê toàn hệ thống (F12.03)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.imaging.domain.entities import TranslationStatus
from app.modules.imaging.infrastructure.orm_models import BubbleModel, TranslationModel
from app.modules.stats.application.dto import ImagingCounts


class SqlImagingCountsSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def imaging_counts(self) -> ImagingCounts:
        async with self._session_factory() as session:
            rows = await session.execute(
                select(TranslationModel.status, func.count()).group_by(TranslationModel.status)
            )
            by_status = {status: int(n) for status, n in rows.all()}
            bubbles = (await session.execute(select(func.count()).select_from(BubbleModel))).scalar_one()
            avg_ms = (
                await session.execute(
                    select(func.avg(TranslationModel.processing_ms)).where(
                        TranslationModel.status == TranslationStatus.DONE.value
                    )
                )
            ).scalar_one()
        return ImagingCounts(
            queued=by_status.get(TranslationStatus.QUEUED.value, 0),
            running=by_status.get(TranslationStatus.RUNNING.value, 0),
            done=by_status.get(TranslationStatus.DONE.value, 0),
            failed=by_status.get(TranslationStatus.FAILED.value, 0),
            bubbles=int(bubbles),
            avg_processing_ms=int(avg_ms) if avg_ms is not None else None,
        )
