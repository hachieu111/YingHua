"""Adapter của M05 với module khác qua giao diện công khai: múi giờ người học (M02)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.application.public import Identity, Role
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork


class SettingsTimezoneSource:
    """Múi giờ đã khai báo của người học, từ M02."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def timezone_of(self, user_id: int) -> str | None:
        identity = Identity(user_id=user_id, role=Role.USER, session_id="")
        use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory))
        return (await use_case.execute(identity)).timezone
