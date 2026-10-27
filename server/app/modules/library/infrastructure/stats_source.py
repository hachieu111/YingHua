"""Số liệu của M03 cho M12 Thống kê: tiến độ đọc từng truyện (F12.02) và đếm nội dung (F12.03)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.library.domain.entities import Visibility
from app.modules.library.infrastructure.orm_models import ChapterModel, PageModel, SeriesModel
from app.modules.library.infrastructure.progress_repository import SqlProgressRepository
from app.modules.stats.application.dto import ContentCounts, SeriesReadingProgress


class SqlReadingProgressSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def series_progress(self, user_id: int, limit: int) -> list[SeriesReadingProgress]:
        async with self._session_factory() as session:
            items = await SqlProgressRepository(session).list_read_series(user_id, limit)
        result: list[SeriesReadingProgress] = []
        for series, progress in items:
            resume = progress.resume
            result.append(
                SeriesReadingProgress(
                    series_id=series.id,
                    title=series.title_vi,
                    cover_file_id=series.cover_file_id,
                    pages_read=progress.pages_read,
                    pages_total=progress.pages_total,
                    percent=progress.percent,
                    last_read_at=resume.updated_at if resume else None,
                    resume_chapter_id=resume.chapter_id if resume else None,
                    resume_page_no=resume.page_no if resume else None,
                    completed=progress.pages_total > 0 and progress.pages_read >= progress.pages_total,
                )
            )
        return result


class SqlContentCountsSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def content_counts(self) -> ContentCounts:
        async with self._session_factory() as session:
            series_total, series_public = (
                await session.execute(
                    select(
                        func.count(),
                        func.count().filter(SeriesModel.visibility == Visibility.PUBLIC.value),
                    ).select_from(SeriesModel)
                )
            ).one()
            chapters = (await session.execute(select(func.count()).select_from(ChapterModel))).scalar_one()
            pages = (await session.execute(select(func.count()).select_from(PageModel))).scalar_one()
        return ContentCounts(int(series_total), int(series_public), int(chapters), int(pages))
