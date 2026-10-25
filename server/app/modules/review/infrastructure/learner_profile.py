"""Trình độ HSK và múi giờ của người học, lấy qua giao diện công khai của M02."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.application.public import Identity, Role
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork


class SettingsLearnerProfileSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def profile_of(self, user_id: int) -> tuple[int | None, str | None]:
        identity = Identity(user_id=user_id, role=Role.USER, session_id="")
        use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory))
        settings = await use_case.execute(identity)
        return settings.hsk_level, settings.timezone
