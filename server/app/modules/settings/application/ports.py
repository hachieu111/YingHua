from __future__ import annotations

from typing import Any, Protocol

from app.modules.admin.application.public import AuditLogRepository
from app.modules.settings.domain.entities import UserSettings


class SettingsRepository(Protocol):
    async def get_or_create(self, user_id: int) -> UserSettings:
        """Trả cài đặt của người dùng; chưa có thì tạo bản mặc định."""
        ...

    async def save(self, settings: UserSettings) -> None: ...


class SettingsUnitOfWork(Protocol):
    @property
    def settings(self) -> SettingsRepository: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    async def __aenter__(self) -> SettingsUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
