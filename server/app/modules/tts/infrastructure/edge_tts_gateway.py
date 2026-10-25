"""Adapter Edge TTS (F11.04): một lần gọi có thời gian chờ; thử lại do use case điều khiển."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import edge_tts

from app.modules.tts.domain.errors import TtsUnavailableError
from app.modules.tts.domain.rules import edge_rate
from app.modules.tts.domain.value_objects import CallStatus


class EdgeTtsGateway:
    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    async def synthesize(self, text: str, voice: str, rate: Decimal) -> bytes:
        try:
            return await asyncio.wait_for(self._collect(text, voice, rate), self._timeout)
        except asyncio.TimeoutError as exc:
            raise TtsUnavailableError(CallStatus.TIMEOUT, "TIMEOUT") from exc
        except TtsUnavailableError:
            raise
        except Exception as exc:
            raise TtsUnavailableError(CallStatus.ERROR, exc.__class__.__name__[:64]) from exc

    @staticmethod
    async def _collect(text: str, voice: str, rate: Decimal) -> bytes:
        communicate = edge_tts.Communicate(text, voice, rate=edge_rate(rate))
        chunks = [part["data"] async for part in communicate.stream() if part["type"] == "audio"]
        if not chunks:
            raise TtsUnavailableError(CallStatus.INVALID, "EMPTY_AUDIO")
        return b"".join(chunks)
