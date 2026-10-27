"""Số liệu người dùng (M01) cho thống kê toàn hệ thống (F12.03)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.domain.entities import Role, UserStatus
from app.modules.auth.infrastructure.orm_models import UserModel
from app.modules.stats.application.dto import UserCounts

NEW_USER_WINDOW = timedelta(days=7)


class SqlUserCountsSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def user_counts(self, now: datetime) -> UserCounts:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(
                        func.count(),
                        func.count().filter(UserModel.role == Role.ADMIN.value),
                        func.count().filter(UserModel.status == UserStatus.LOCKED.value),
                        func.count().filter(UserModel.created_at >= now - NEW_USER_WINDOW),
                    ).select_from(UserModel)
                )
            ).one()
        return UserCounts(*(int(v) for v in row))
