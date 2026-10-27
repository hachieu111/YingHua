"""Ghi hoạt động học vào `daily_activities` trên CÙNG phiên (giao dịch) với hành động của module khác."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.infrastructure.public import SqlTimezoneReader
from app.modules.stats.domain.activity import ActivityDelta, local_date
from app.modules.stats.infrastructure.repositories import SqlActivityRepository


class SqlActivityRecorder:
    """Hiện thực `ActivityRecorder`: tính ngày theo múi giờ của người học rồi cộng dồn bộ đếm."""

    def __init__(self, session: AsyncSession) -> None:
        self._activity = SqlActivityRepository(session)
        self._timezones = SqlTimezoneReader(session)

    async def record(self, user_id: int, at: datetime, delta: ActivityDelta) -> None:
        tz_name = await self._timezones.timezone_of(user_id)
        await self._activity.add(user_id, local_date(at, tz_name), delta, at)
