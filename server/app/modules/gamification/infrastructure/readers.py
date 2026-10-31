"""Đọc dữ liệu của module khác (M01 hồ sơ, M02 cài đặt, M12 bộ đếm ngày) cho M16."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.gamification.application.dto import DayCounters, UserProfile
from app.modules.gamification.infrastructure.foreign_tables import daily_activities as da
from app.modules.gamification.infrastructure.foreign_tables import user_settings as us
from app.modules.gamification.infrastructure.foreign_tables import users

DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"


class SqlUserDirectory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def profile(self, user_id: int) -> UserProfile:
        row = (
            await self._session.execute(
                select(
                    users.c.display_name,
                    users.c.avatar_file_id,
                    users.c.avatar_preset,
                    us.c.timezone,
                    us.c.weekly_page_goal,
                    us.c.hsk_level,
                    us.c.show_on_leaderboard,
                )
                .select_from(users.outerjoin(us, us.c.user_id == users.c.id))
                .where(users.c.id == user_id)
            )
        ).first()
        if row is None:
            raise NotFoundError("Không tìm thấy người dùng")
        return UserProfile(
            user_id=user_id,
            timezone=row[3] or DEFAULT_TIMEZONE,
            weekly_page_goal=row[4],
            hsk_level=row[5],
            show_on_leaderboard=True if row[6] is None else bool(row[6]),
            display_name=str(row[0]),
            avatar_file_id=row[1],
            avatar_preset=row[2],
        )


class SqlActivityReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def day_counters(self, user_id: int, day: date) -> DayCounters:
        row = (
            await self._session.execute(
                select(da.c.pages_read, da.c.reviews_count).where(
                    da.c.user_id == user_id, da.c.activity_date == day
                )
            )
        ).first()
        return DayCounters(int(row[0]), int(row[1])) if row else DayCounters()

    async def pages_between(self, user_id: int, start: date, end: date) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(da.c.pages_read), 0)).where(
                da.c.user_id == user_id, da.c.activity_date >= start, da.c.activity_date <= end
            )
        )
        return int(total or 0)

    async def study_days(self, user_id: int) -> list[date]:
        rows = await self._session.scalars(
            select(da.c.activity_date)
            .where(da.c.user_id == user_id, da.c.reviews_count + da.c.pages_read > 0)
            .order_by(da.c.activity_date)
        )
        return list(rows)
