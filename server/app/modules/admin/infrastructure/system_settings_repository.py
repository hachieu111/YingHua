from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.admin.application.dto import SamplePageCandidate
from app.modules.admin.infrastructure import foreign_tables as ft
from app.modules.admin.infrastructure.orm_models import SystemSettingModel


class SqlSystemSettingsRepository:
    """Bảng `system_settings` trong giao dịch của quản trị (F13.05)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_all(self) -> dict[str, Any]:
        rows = await self._session.execute(select(SystemSettingModel.key, SystemSettingModel.value))
        return {key: value for key, value in rows.all()}

    async def upsert_many(self, values: dict[str, Any], admin_id: int, at: datetime) -> None:
        for key, value in values.items():
            stmt = insert(SystemSettingModel).values(key=key, value=value, updated_by=admin_id, updated_at=at)
            await self._session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[SystemSettingModel.key],
                    set_={"value": stmt.excluded.value, "updated_by": admin_id, "updated_at": at},
                )
            )

    async def delete_many(self, keys: list[str]) -> None:
        if keys:
            await self._session.execute(delete(SystemSettingModel).where(SystemSettingModel.key.in_(keys)))

    async def is_valid_sample_page(self, page_id: int) -> bool:
        query = _sample_page_query(ft.pages.c.id).where(ft.pages.c.id == page_id)
        return (await self._session.execute(query)).first() is not None

    async def list_sample_page_candidates(self, limit: int) -> list[SamplePageCandidate]:
        bubble_count = (
            select(func.count())
            .where(ft.bubbles.c.translation_id == ft.pages.c.translation_id, ft.bubbles.c.text_zh != "")
            .scalar_subquery()
        )
        query = (
            _sample_page_query(
                ft.pages.c.id,
                ft.series.c.title_vi,
                ft.chapters.c.number,
                ft.chapters.c.title,
                ft.pages.c.page_no,
                bubble_count,
            )
            .order_by(ft.pages.c.id.desc())
            .limit(limit)
        )
        rows = await self._session.execute(query)
        return [
            SamplePageCandidate(page_id, title, number, chapter_title, page_no, count)
            for page_id, title, number, chapter_title, page_no, count in rows.all()
        ]


def _sample_page_query(*columns: Any) -> Select[Any]:
    """Điều kiện trang mẫu hợp lệ (F04.16): truyện công khai, bản dịch xong, ảnh gốc chưa bị gỡ."""
    return (
        select(*columns)
        .select_from(
            ft.pages.join(ft.chapters, ft.chapters.c.id == ft.pages.c.chapter_id)
            .join(ft.series, ft.series.c.id == ft.chapters.c.series_id)
            .join(ft.translations, ft.translations.c.id == ft.pages.c.translation_id)
            .join(ft.stored_files, ft.stored_files.c.id == ft.pages.c.original_file_id)
        )
        .where(
            ft.series.c.visibility == "public",
            ft.translations.c.status == "done",
            ft.stored_files.c.removed_at.is_(None),
        )
    )


class SqlSystemSettingsSource:
    """Đọc `system_settings` bằng giao dịch riêng, cho bộ đệm cấu hình dùng chung cả tiến trình."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load_all(self) -> dict[str, Any]:
        async with self._session_factory() as session:
            return await SqlSystemSettingsRepository(session).load_all()
