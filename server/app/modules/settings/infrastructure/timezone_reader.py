"""Đọc múi giờ của người học trên cùng phiên với giao dịch của module khác (M12 ghi hoạt động theo ngày)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.domain.entities import DEFAULT_TIMEZONE
from app.modules.settings.infrastructure.orm_models import UserSettingsModel


class SqlTimezoneReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def timezone_of(self, user_id: int) -> str:
        """Múi giờ đã lưu; chưa có dòng cài đặt thì dùng mặc định. Không khóa dòng, không tạo dòng."""
        result = await self._session.execute(
            select(UserSettingsModel.timezone).where(UserSettingsModel.user_id == user_id)
        )
        return result.scalar_one_or_none() or DEFAULT_TIMEZONE
