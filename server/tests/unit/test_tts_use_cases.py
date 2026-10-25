"""M11 Phát âm — F11.01, F11.03–F11.06 (US-NH-53, US-NH-55, US-TTS-01..03), dùng gateway giả."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.core.errors import PayloadTooLargeError
from app.modules.tts.application.dto import SynthesizeCommand
from app.modules.tts.domain.errors import (
    TtsDisabledError,
    TtsRateLimitedError,
    TtsTextEmptyError,
    TtsTextTooLongError,
    TtsUnavailableError,
)
from app.modules.tts.domain.rules import DEFAULT_VOICE, GUEST_MAX_CHARS, MAX_REQUEST_CHARS
from app.modules.tts.domain.value_objects import CallStatus
from tests.unit.tts_fakes import AUDIO, USER, FakeGateway, Harness


def cmd(text: str = "你好", **kwargs: object) -> SynthesizeCommand:
    base: dict[str, object] = {"identity": USER, "client_key": "1.2.3.4"}
    base.update(kwargs)
    return SynthesizeCommand(text=text, **base)  # type: ignore[arg-type]


async def test_second_request_is_served_from_cache_without_calling_gateway() -> None:
    """US-TTS-02: nghe lại cùng nội dung không gọi dịch vụ ngoài."""
    h = Harness()
    first = await h.use_case.execute(cmd())
    second = await h.use_case.execute(cmd("  你好 "))  # khoảng trắng thừa vẫn cùng khóa
    assert (first.cache_hit, second.cache_hit) == (False, True)
    assert second.audio == AUDIO
    assert len(h.gateway.calls) == 1


async def test_different_voice_or_rate_is_a_different_cache_key() -> None:
    """F11.05: cùng văn bản nhưng khác giọng/tốc độ tạo bản mới."""
    h = Harness()
    await h.use_case.execute(cmd())
    await h.use_case.execute(cmd(voice="zh-CN-YunxiNeural"))
    await h.use_case.execute(cmd(rate=Decimal("0.8")))
    assert len(h.gateway.calls) == 3
    assert h.cache.stores == 3


async def test_concurrent_identical_requests_call_gateway_once() -> None:
    """F11.05: 5 yêu cầu cùng khóa cùng lúc chỉ gọi Edge TTS một lần."""
    h = Harness(FakeGateway(delay=0.05))
    results = await asyncio.gather(*(h.use_case.execute(cmd()) for _ in range(5)))
    assert len(h.gateway.calls) == 1
    assert all(r.audio == AUDIO for r in results)
    assert h.cache.stores == 1
    assert h.flight.pending == 0


async def test_gateway_failure_is_not_cached_and_raises_unavailable() -> None:
    """F11.06: không lưu cache khi lỗi; lỗi được ghi nhật ký."""
    h = Harness(FakeGateway(fail_times=99))
    with pytest.raises(TtsUnavailableError) as info:
        await h.use_case.execute(cmd())
    assert info.value.message == "Không phát được âm thanh, thử lại sau"
    assert h.cache.stores == 0
    assert len(h.gateway.calls) == 2  # lần đầu + đúng 1 lần thử lại
    assert h.sleeps == [0.5]
    assert [e.status for e in h.call_log.entries] == [CallStatus.ERROR, CallStatus.ERROR]
    assert h.flight.pending == 0


async def test_one_retry_recovers_from_a_transient_failure() -> None:
    h = Harness(FakeGateway(fail_times=1, failure=CallStatus.TIMEOUT))
    result = await h.use_case.execute(cmd())
    assert result.audio == AUDIO
    assert [e.status for e in h.call_log.entries] == [CallStatus.TIMEOUT, CallStatus.OK]
    assert all(e.error_code in (None, "FAKE") for e in h.call_log.entries)


async def test_empty_audio_from_gateway_is_never_cached() -> None:
    """F11.06: âm thanh rỗng/hỏng không vào bộ đệm."""
    gateway = FakeGateway()
    gateway.audio = b""
    h = Harness(gateway)
    with pytest.raises(TtsUnavailableError):
        await h.use_case.execute(cmd())
    assert h.cache.stores == 0
    assert h.call_log.entries[0].status is CallStatus.INVALID


async def test_missing_cache_file_is_regenerated_and_replaced() -> None:
    """F11.05 ngoại lệ: tệp bộ đệm mất thì tạo lại."""
    h = Harness()
    await h.use_case.execute(cmd())
    key = next(iter(h.cache.rows))
    h.cache.rows[key] = (h.cache.rows[key][0], None)  # tệp trong kho mất
    result = await h.use_case.execute(cmd())
    assert result.cache_hit is False
    assert len(h.gateway.calls) == 2
    assert h.cache.rows[key][1] == AUDIO


async def test_cached_audio_plays_even_when_service_is_down() -> None:
    """F11.06: không có mạng thì âm thanh đã có trong bộ đệm vẫn phát được."""
    h = Harness()
    await h.use_case.execute(cmd())
    h.gateway.fail_times = 99
    result = await h.use_case.execute(cmd())
    assert result.cache_hit is True


async def test_empty_text_is_rejected_without_calling_gateway() -> None:
    h = Harness()
    with pytest.raises(TtsTextEmptyError):
        await h.use_case.execute(cmd("   \n "))
    assert h.gateway.calls == []


async def test_text_over_request_limit_is_rejected() -> None:
    h = Harness()
    with pytest.raises(TtsTextTooLongError) as info:
        await h.use_case.execute(cmd("字" * (MAX_REQUEST_CHARS + 1)))
    assert isinstance(info.value, PayloadTooLargeError)
    assert h.gateway.calls == []


async def test_long_text_is_split_by_sentence_and_joined() -> None:
    """F11.04: văn bản dài chia theo câu, ghép âm thanh, lưu một bản đệm."""
    h = Harness()
    sentence = "这是一个比较长的句子，" + "字" * 200 + "。"
    result = await h.use_case.execute(cmd(sentence * 4))
    assert len(h.gateway.calls) > 1
    assert all(len(call[0]) <= 500 for call in h.gateway.calls)
    assert result.audio == AUDIO * len(h.gateway.calls)
    assert h.cache.stores == 1


async def test_unknown_voice_falls_back_to_default_and_flags_it() -> None:
    """F11.01/F02.03: giọng không khả dụng -> giọng mặc định + báo đã chuyển."""
    h = Harness()
    result = await h.use_case.execute(cmd(voice="xx-XX-NoSuchNeural"))
    assert (result.voice, result.voice_fallback) == (DEFAULT_VOICE, True)
    assert h.gateway.calls[0][1] == DEFAULT_VOICE


async def test_voice_defaults_to_personal_setting() -> None:
    h = Harness()
    h.voices.voice = "zh-CN-YunxiNeural"
    result = await h.use_case.execute(cmd())
    assert (result.voice, result.voice_fallback) == ("zh-CN-YunxiNeural", False)


async def test_rate_outside_range_is_clamped_to_nearest_bound() -> None:
    """F11.03: 0,5x–1,5x."""
    h = Harness()
    slow = await h.use_case.execute(cmd(rate=Decimal("0.1")))
    fast = await h.use_case.execute(cmd(rate=Decimal("3")))
    assert (slow.rate, fast.rate) == (Decimal("0.50"), Decimal("1.50"))


async def test_disabled_tts_returns_disabled_error() -> None:
    h = Harness(enabled=False)
    with pytest.raises(TtsDisabledError):
        await h.use_case.execute(cmd())


async def test_guest_text_is_limited_and_cache_misses_are_rate_limited() -> None:
    h = Harness()
    guest = {"identity": None}
    with pytest.raises(TtsTextTooLongError):
        await h.use_case.execute(cmd("字" * (GUEST_MAX_CHARS + 1), **guest))
    for i in range(3):  # guest_max_requests = 3 lượt gọi dịch vụ ngoài
        await h.use_case.execute(cmd(f"字{i}", **guest))
    with pytest.raises(TtsRateLimitedError):
        await h.use_case.execute(cmd("字9", **guest))
    assert (await h.use_case.execute(cmd("字0", **guest))).cache_hit is True  # nghe lại bản đệm vẫn được
