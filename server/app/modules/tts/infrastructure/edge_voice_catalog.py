"""Danh sách giọng của Edge TTS (F11.03): một lần gọi có thời gian chờ; lỗi đổi thành lỗi của port."""

from __future__ import annotations

import asyncio

import edge_tts

from app.modules.tts.domain.errors import TtsUnavailableError
from app.modules.tts.domain.value_objects import CallStatus
from app.modules.tts.domain.voices import VoiceInfo, voices_from_service


class EdgeVoiceCatalog:
    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    async def list_voices(self) -> list[VoiceInfo]:
        try:
            raw = await asyncio.wait_for(edge_tts.list_voices(), self._timeout)
        except asyncio.TimeoutError as exc:
            raise TtsUnavailableError(CallStatus.TIMEOUT, "TIMEOUT") from exc
        except Exception as exc:
            raise TtsUnavailableError(CallStatus.ERROR, exc.__class__.__name__[:64]) from exc
        return voices_from_service(raw)
