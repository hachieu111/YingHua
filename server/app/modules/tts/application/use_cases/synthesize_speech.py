from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.core.clock import Clock
from app.core.errors import DomainError, NotFoundError
from app.core.rate_limit import FailureLimiter
from app.core.single_flight import SingleFlight
from app.modules.tts.application.dto import SpeechAudio, SynthesizeCommand
from app.modules.tts.application.ports import (
    CachedAudio,
    ExternalCallEntry,
    ExternalCallLog,
    TtsCacheRepository,
    TtsGateway,
    VoicePreferences,
)
from app.modules.tts.domain.errors import TtsDisabledError, TtsRateLimitedError, TtsUnavailableError
from app.modules.tts.domain.rules import (
    MAX_RETRIES,
    MIN_AUDIO_BYTES,
    RETRY_BACKOFF_SECONDS,
    normalize_rate,
    normalize_text,
    resolve_voice,
    split_into_chunks,
    text_digest,
    validate_text,
)
from app.modules.tts.domain.value_objects import CallStatus

logger = logging.getLogger(__name__)

PROVIDER = "edge-tts"
OPERATION = "synthesize"


@dataclass(frozen=True, slots=True)
class TtsPolicy:
    enabled: bool
    guest_max_requests: int  # số lần Khách được gọi dịch vụ ngoài (không tính cache) trong một cửa sổ


class SynthesizeSpeechUseCase:
    """F11.01, F11.03, F11.04, F11.05, F11.06 — US-NH-53, US-NH-55, US-TTS-01..03.

    Chuẩn hóa văn bản -> tra bộ đệm -> (chưa có) gọi Edge TTS một lần cho mọi yêu cầu trùng khóa -> lưu đệm.
    """

    def __init__(
        self,
        gateway: TtsGateway,
        cache: TtsCacheRepository,
        call_log: ExternalCallLog,
        voices: VoicePreferences,
        flight: SingleFlight,
        guest_limiter: FailureLimiter,
        clock: Clock,
        policy: TtsPolicy,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._gateway = gateway
        self._cache = cache
        self._call_log = call_log
        self._voices = voices
        self._flight = flight
        self._guest_limiter = guest_limiter
        self._clock = clock
        self._policy = policy
        self._sleep = sleep

    async def execute(self, command: SynthesizeCommand) -> SpeechAudio:
        if not self._policy.enabled:
            raise TtsDisabledError()
        is_guest = command.identity is None
        text = normalize_text(command.text)
        validate_text(text, is_guest)
        preferred = None if command.identity is None else await self._voices.get_voice(command.identity)
        voice, fallback = resolve_voice(command.voice, preferred)
        if fallback:
            logger.warning("Giọng TTS không khả dụng, dùng giọng mặc định")
        rate = normalize_rate(command.rate)
        digest = text_digest(text)

        cached = await self._read_cache(digest, voice, rate)
        if cached is not None:
            return SpeechAudio(cached, voice, rate, fallback, cache_hit=True)
        if is_guest:
            self._check_guest_limit(command.client_key)
        audio = await self._flight.run(
            f"{digest}|{voice}|{rate}", lambda: self._produce(text, digest, voice, rate)
        )
        return SpeechAudio(audio, voice, rate, fallback, cache_hit=False)

    def _check_guest_limit(self, client_key: str) -> None:
        key = f"tts:{client_key}"
        if self._guest_limiter.is_blocked(key, self._policy.guest_max_requests):
            raise TtsRateLimitedError()
        self._guest_limiter.record_failure(key)  # dùng như bộ đếm lượt gọi dịch vụ ngoài

    async def _read_cache(self, digest: str, voice: str, rate: Decimal) -> bytes | None:
        """Âm thanh trong bộ đệm nếu còn đọc được; tệp mất/hỏng coi như chưa có (F11.05 ngoại lệ)."""
        cached = await self._cache.find(digest, voice, rate)
        if cached is None:
            return None
        return await self._load(cached)

    async def _load(self, cached: CachedAudio) -> bytes | None:
        try:
            audio = await self._cache.read(cached)
        except NotFoundError:
            logger.warning("Tệp âm thanh trong bộ đệm đã mất, sẽ tạo lại (cache_id=%s)", cached.cache_id)
            return None
        if len(audio) < MIN_AUDIO_BYTES:
            logger.warning("Tệp âm thanh trong bộ đệm hỏng, sẽ tạo lại (cache_id=%s)", cached.cache_id)
            return None
        return audio

    async def _produce(self, text: str, digest: str, voice: str, rate: Decimal) -> bytes:
        # Kiểm lại: tiến trình khác có thể vừa tạo xong trong lúc ta chờ (UNIQUE ở CSDL lo phần ghi).
        existing = await self._read_cache(digest, voice, rate)
        if existing is not None:
            return existing
        parts = [await self._call_with_retry(chunk, voice, rate) for chunk in split_into_chunks(text)]
        audio = b"".join(parts)
        try:
            await self._cache.store(digest, voice, rate, audio, self._clock.now())
        except DomainError:
            # Không lưu được bộ đệm (kho tệp lỗi) thì vẫn phát được lần này.
            logger.warning("Không lưu được âm thanh vào bộ đệm", exc_info=True)
        return audio

    async def _call_with_retry(self, text: str, voice: str, rate: Decimal) -> bytes:
        attempt = 0
        while True:
            started = self._clock.now()
            try:
                audio = await self._gateway.synthesize(text, voice, rate)
                if len(audio) < MIN_AUDIO_BYTES:
                    raise TtsUnavailableError(CallStatus.INVALID, "EMPTY_AUDIO")
            except TtsUnavailableError as exc:
                await self._log(started, exc.failure, exc.reason)
                logger.warning(
                    "Edge TTS lỗi (%s, %s), lần thử %d", exc.failure.value, exc.reason, attempt + 1
                )
                if attempt >= MAX_RETRIES:
                    raise
                await self._sleep(RETRY_BACKOFF_SECONDS * (2**attempt))
                attempt += 1
            else:
                await self._log(started, CallStatus.OK, None)
                return audio

    async def _log(self, started: datetime, status: CallStatus, error_code: str | None) -> None:
        elapsed = self._clock.now() - started
        await self._call_log.record(
            ExternalCallEntry(PROVIDER, OPERATION, status, int(elapsed.total_seconds() * 1000), error_code)
        )
