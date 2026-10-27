from __future__ import annotations

from app.modules.admin.application.dto import SystemStatus
from app.modules.admin.application.system_settings import SystemSettingsPort


class GetSystemStatusUseCase:
    """F13.05 — Trạng thái công khai của hệ thống (US-QT-13 TC3, TC5; US-NH-77 TC5).

    Gồm bảo trì, LLM, TTS và có trang mẫu hay không; không lộ hạn mức hay giá trị nội bộ.
    """

    def __init__(self, settings: SystemSettingsPort) -> None:
        self._settings = settings

    async def execute(self) -> SystemStatus:
        s = await self._settings.snapshot()
        return SystemStatus(
            maintenance_mode=s.maintenance_mode,
            llm_enabled=s.llm_enabled,
            tts_enabled=s.tts_enabled,
            sample_page_available=s.sample_page_id is not None,
        )
