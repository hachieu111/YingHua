"""Danh sách người học đã bật nhắc ôn (F14.03) cho tác vụ nhắc ôn của M14 (F14.04)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.domain.entities import ReminderSetting
from app.modules.settings.infrastructure.orm_models import UserSettingsModel as Row


class SqlReminderSettingsSource:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_enabled(self, after_user_id: int, limit: int) -> list[ReminderSetting]:
        """Theo thứ tự `user_id` tăng dần, bắt đầu sau `after_user_id` (phân trang kiểu keyset)."""
        rows = await self._session.execute(
            select(Row.user_id, Row.timezone, Row.reminder_time)
            .where(
                Row.reminder_enabled.is_(True), Row.reminder_time.is_not(None), Row.user_id > after_user_id
            )
            .order_by(Row.user_id)
            .limit(limit)
        )
        return [ReminderSetting(uid, tz, at) for uid, tz, at in rows.all() if at is not None]
