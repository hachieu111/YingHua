from __future__ import annotations

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import SystemSettingsView
from app.modules.admin.application.system_settings import CachedSystemSettings
from app.modules.auth.application.public import Identity


class GetSystemSettingsUseCase:
    """F13.05 — Xem cấu hình hệ thống hiện hành (US-QT-13). Giá trị đọc mới, không qua bộ đệm."""

    def __init__(self, settings: CachedSystemSettings) -> None:
        self._settings = settings

    async def execute(self, actor: Identity) -> SystemSettingsView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        self._settings.invalidate()
        return SystemSettingsView(await self._settings.snapshot(), await self._settings.overridden_keys())
