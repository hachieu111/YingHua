"""Múi giờ của người học, lấy qua giao diện công khai của M02."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.application.public import Identity
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork


class SettingsTimezoneSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def timezone_of(self, identity: Identity, owner_id: int) -> str:
        use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory))
        return (await use_case.execute(identity, owner_id)).timezone
