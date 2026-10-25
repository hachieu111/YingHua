"""M11 Phát âm qua API — F11.01, F11.03, F11.05, F11.06 (US-NH-53, US-NH-55, US-TTS-01..03).

Gateway luôn là bản giả (gắn bằng dependency override); bộ đệm dùng CSDL và kho tệp thật của test.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import text

from app.container import Container, get_container
from app.modules.tts.api.dependencies import get_synthesize_speech
from app.modules.tts.application.use_cases.synthesize_speech import SynthesizeSpeechUseCase, TtsPolicy
from app.modules.tts.infrastructure.call_log import SqlExternalCallLog
from app.modules.tts.infrastructure.repositories import SqlTtsCacheRepository
from app.modules.tts.infrastructure.voice_preferences import SettingsVoicePreferences
from tests.helpers import error_code, register
from tests.unit.tts_fakes import AUDIO, FakeGateway

pytestmark = pytest.mark.integration

URL = "/api/v1/tts"


@pytest.fixture
def gateway(app: FastAPI) -> Iterator[FakeGateway]:
    fake = FakeGateway()
    fake.enabled = True  # type: ignore[attr-defined]

    def override(container: Container = Depends(get_container)) -> SynthesizeSpeechUseCase:
        return SynthesizeSpeechUseCase(
            gateway=fake,
            cache=SqlTtsCacheRepository(container.session_factory, container.storage),
            call_log=SqlExternalCallLog(container.session_factory),
            voices=SettingsVoicePreferences(container.session_factory),
            flight=container.single_flight,
            guest_limiter=container.guest_tts_limiter,
            clock=container.clock,
            policy=TtsPolicy(enabled=fake.enabled, guest_max_requests=2),  # type: ignore[attr-defined]
        )

    app.dependency_overrides[get_synthesize_speech] = override
    yield fake
    app.dependency_overrides.pop(get_synthesize_speech, None)


async def _count(app: FastAPI, sql: str) -> int:
    async with app.state.container.session_factory() as session:
        return int((await session.execute(text(sql))).scalar_one())


async def test_speak_returns_mp3_with_headers_then_hits_cache(
    client: httpx.AsyncClient, gateway: FakeGateway
) -> None:
    who = await register(client)
    word = f"你好{who.id}"
    first = await client.post(URL, json={"text": word}, headers=who.headers)
    assert first.status_code == 200
    assert first.headers["content-type"] == "audio/mpeg"
    assert first.content == AUDIO
    assert first.headers["x-tts-cache"] == "miss"
    assert first.headers["x-tts-voice"] == "zh-CN-XiaoxiaoNeural"
    assert first.headers["x-tts-rate"] == "1.00"
    assert first.headers["x-tts-voice-fallback"] == "false"
    second = await client.post(URL, json={"text": word}, headers=who.headers)
    assert second.headers["x-tts-cache"] == "hit"
    assert len(gateway.calls) == 1


async def test_voice_comes_from_settings_and_unknown_voice_falls_back(
    client: httpx.AsyncClient, gateway: FakeGateway
) -> None:
    who = await register(client)
    await client.patch("/api/v1/settings", json={"tts_voice": "zh-CN-YunxiNeural"}, headers=who.headers)
    res = await client.post(URL, json={"text": f"男{who.id}"}, headers=who.headers)
    assert res.headers["x-tts-voice"] == "zh-CN-YunxiNeural"
    bad = await client.post(
        URL, json={"text": f"男{who.id}", "voice": "xx-XX-FooNeural"}, headers=who.headers
    )
    assert bad.headers["x-tts-voice"] == "zh-CN-XiaoxiaoNeural"
    assert bad.headers["x-tts-voice-fallback"] == "true"


async def test_rate_is_part_of_cache_key_and_clamped(client: httpx.AsyncClient, gateway: FakeGateway) -> None:
    who = await register(client)
    word = f"快{who.id}"
    await client.post(URL, json={"text": word, "rate": 0.8}, headers=who.headers)
    await client.post(URL, json={"text": word, "rate": 1.2}, headers=who.headers)
    res = await client.post(URL, json={"text": word, "rate": 5}, headers=who.headers)
    assert res.headers["x-tts-rate"] == "1.50"
    assert len(gateway.calls) == 3


async def test_concurrent_requests_call_gateway_once(client: httpx.AsyncClient, gateway: FakeGateway) -> None:
    gateway.delay = 0.1
    who = await register(client)
    word = f"并发{who.id}"
    results = await asyncio.gather(
        *(client.post(URL, json={"text": word}, headers=who.headers) for _ in range(5))
    )
    assert [r.status_code for r in results] == [200] * 5
    assert len(gateway.calls) == 1


async def test_empty_text_returns_400_and_too_long_returns_413(
    client: httpx.AsyncClient, gateway: FakeGateway
) -> None:
    who = await register(client)
    empty = await client.post(URL, json={"text": "  "}, headers=who.headers)
    assert (empty.status_code, error_code(empty)) == (400, "TTS_TEXT_EMPTY")
    long = await client.post(URL, json={"text": "字" * 2001}, headers=who.headers)
    assert (long.status_code, error_code(long)) == (413, "TTS_TEXT_TOO_LONG")
    assert gateway.calls == []


async def test_service_failure_returns_503_without_caching_and_logs_calls(
    app: FastAPI, client: httpx.AsyncClient, gateway: FakeGateway
) -> None:
    gateway.fail_times = 99
    who = await register(client)
    before_cache = await _count(app, "SELECT count(*) FROM tts_cache")
    before_logs = await _count(app, "SELECT count(*) FROM external_call_logs WHERE status = 'error'")
    res = await client.post(URL, json={"text": f"坏{who.id}"}, headers=who.headers)
    assert res.status_code == 503
    assert error_code(res) == "TTS_UNAVAILABLE"
    assert res.json()["error"]["message"] == "Không phát được âm thanh, thử lại sau"
    assert "FAKE" not in res.text and "Traceback" not in res.text
    assert await _count(app, "SELECT count(*) FROM tts_cache") == before_cache
    assert (
        await _count(app, "SELECT count(*) FROM external_call_logs WHERE status = 'error'") == before_logs + 2
    )


async def test_cache_file_lost_is_regenerated(
    app: FastAPI, client: httpx.AsyncClient, gateway: FakeGateway
) -> None:
    who = await register(client)
    word = f"丢{who.id}"
    await client.post(URL, json={"text": word}, headers=who.headers)
    async with app.state.container.session_factory() as session:
        key = (
            await session.execute(
                text(
                    "SELECT f.storage_key FROM tts_cache c JOIN stored_files f ON f.id = c.file_id "
                    "ORDER BY c.id DESC LIMIT 1"
                )
            )
        ).scalar_one()
    await app.state.container.storage.delete(key)
    res = await client.post(URL, json={"text": word}, headers=who.headers)
    assert res.status_code == 200
    assert res.headers["x-tts-cache"] == "miss"
    assert len(gateway.calls) == 2
    again = await client.post(URL, json={"text": word}, headers=who.headers)
    assert again.headers["x-tts-cache"] == "hit"


async def test_disabled_tts_returns_503_disabled(client: httpx.AsyncClient, gateway: FakeGateway) -> None:
    gateway.enabled = False  # type: ignore[attr-defined]
    res = await client.post(URL, json={"text": "你好"})
    assert (res.status_code, error_code(res)) == (503, "TTS_DISABLED")


async def test_guest_can_listen_short_text_but_is_limited(
    client: httpx.AsyncClient, gateway: FakeGateway
) -> None:
    word = f"客{id(gateway)}"
    assert (await client.post(URL, json={"text": word})).status_code == 200
    too_long = await client.post(URL, json={"text": "字" * 101})
    assert (too_long.status_code, error_code(too_long)) == (413, "TTS_TEXT_TOO_LONG")
    assert (await client.post(URL, json={"text": word + "二"})).status_code == 200
    limited = await client.post(URL, json={"text": word + "三"})
    assert (limited.status_code, error_code(limited)) == (429, "TTS_RATE_LIMITED")
    assert (await client.post(URL, json={"text": word})).status_code == 200  # bản đệm vẫn nghe được
