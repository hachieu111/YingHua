"""EdgeTtsGateway: đổi lỗi/timeout của thư viện thành lỗi của port (F11.04, F11.06). Không gọi mạng."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.tts.domain.errors import TtsUnavailableError
from app.modules.tts.domain.value_objects import CallStatus
from app.modules.tts.infrastructure.edge_tts_gateway import EdgeTtsGateway


async def test_slow_service_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow(text: str, voice: str, rate: Decimal) -> bytes:
        await asyncio.sleep(5)
        return b"x"

    monkeypatch.setattr(EdgeTtsGateway, "_collect", staticmethod(slow))
    with pytest.raises(TtsUnavailableError) as info:
        await EdgeTtsGateway(0.05).synthesize("你好", "zh-CN-XiaoxiaoNeural", Decimal("1.00"))
    assert info.value.failure is CallStatus.TIMEOUT


async def test_library_error_becomes_port_error_without_leaking_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def broken(text: str, voice: str, rate: Decimal) -> bytes:
        raise ConnectionError("dns secret detail")

    monkeypatch.setattr(EdgeTtsGateway, "_collect", staticmethod(broken))
    with pytest.raises(TtsUnavailableError) as info:
        await EdgeTtsGateway(1).synthesize("你好", "zh-CN-XiaoxiaoNeural", Decimal("1.00"))
    assert info.value.failure is CallStatus.ERROR
    assert info.value.reason == "ConnectionError"
    assert "secret" not in info.value.message
