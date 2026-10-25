"""Trang người học đã đọc (bảng page_reads) cho module khác dùng qua giao diện công khai (F09.09)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library.application.dto import ReadPageRef
from app.modules.library.infrastructure.orm_models import (
    ChapterModel,
    PageModel,
    PageReadModel,
    SeriesModel,
)


class SqlReadPagesSource:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent_read_pages(self, user_id: int, limit: int) -> list[ReadPageRef]:
        """Các trang đã đọc có bản dịch, đọc gần nhất trước, kèm tên truyện."""
        rows = await self._session.execute(
            select(PageModel.translation_id, SeriesModel.title_vi)
            .select_from(PageReadModel)
            .join(PageModel, PageModel.id == PageReadModel.page_id)
            .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .join(SeriesModel, SeriesModel.id == ChapterModel.series_id)
            .where(PageReadModel.user_id == user_id, PageModel.translation_id.is_not(None))
            .order_by(PageReadModel.first_read_at.desc())
            .limit(limit)
        )
        return [ReadPageRef(translation_id, title) for translation_id, title in rows.all() if translation_id]
