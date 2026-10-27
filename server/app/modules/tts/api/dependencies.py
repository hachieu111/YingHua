from __future__ import annotations

from fastapi import Depends

from app.container import Container, get_container
from app.modules.tts.application.use_cases.list_voices import ListVoicesUseCase
from app.modules.tts.application.use_cases.synthesize_speech import SynthesizeSpeechUseCase, TtsPolicy
from app.modules.tts.infrastructure.call_log import SqlExternalCallLog
from app.modules.tts.infrastructure.edge_tts_gateway import EdgeTtsGateway
from app.modules.tts.infrastructure.edge_voice_catalog import EdgeVoiceCatalog
from app.modules.tts.infrastructure.repositories import SqlTtsCacheRepository
from app.modules.tts.infrastructure.voice_preferences import SettingsVoicePreferences


async def get_synthesize_speech(container: Container = Depends(get_container)) -> SynthesizeSpeechUseCase:
    """Lắp use case; test API ghi đè dependency này bằng gateway giả.

    Công tắc TTS đọc từ cấu hình hệ thống mỗi yêu cầu (F13.05) nên quản trị bật/tắt có hiệu lực ngay.
    """
    settings = container.settings
    tts_enabled = (await container.system_settings.snapshot()).tts_enabled
    return SynthesizeSpeechUseCase(
        gateway=EdgeTtsGateway(settings.tts_timeout_seconds),
        cache=SqlTtsCacheRepository(container.session_factory, container.storage),
        call_log=SqlExternalCallLog(container.session_factory),
        voices=SettingsVoicePreferences(container.session_factory),
        flight=container.single_flight,
        guest_limiter=container.guest_tts_limiter,
        clock=container.clock,
        policy=TtsPolicy(enabled=tts_enabled, guest_max_requests=settings.guest_tts_max_requests),
    )


def get_list_voices(container: Container = Depends(get_container)) -> ListVoicesUseCase:
    """Lắp use case; test API ghi đè dependency này bằng danh mục giọng giả."""
    return ListVoicesUseCase(
        EdgeVoiceCatalog(container.settings.tts_timeout_seconds), container.voices_cache, container.clock
    )
