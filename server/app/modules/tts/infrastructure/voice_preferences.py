from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.application.public import Identity
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork


class SettingsVoicePreferences:
    """Đọc giọng đọc từ M02 qua bề mặt công khai của module đó."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(session_factory))

    async def get_voice(self, identity: Identity) -> str | None:
        return (await self._use_case.execute(identity)).tts_voice
