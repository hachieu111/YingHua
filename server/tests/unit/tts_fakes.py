"""Bản giả của M11 cho test: không mạng, không CSDL."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.errors import NotFoundError
from app.core.rate_limit import FailureLimiter
from app.core.single_flight import SingleFlight
from app.modules.auth.application.public import Identity
from app.modules.auth.domain.entities import Role
from app.modules.tts.application.ports import CachedAudio, ExternalCallEntry
from app.modules.tts.application.use_cases.synthesize_speech import SynthesizeSpeechUseCase, TtsPolicy
from app.modules.tts.domain.errors import TtsUnavailableError
from app.modules.tts.domain.value_objects import CallStatus

AUDIO = b"ID3" + b"\x01" * 600  # đủ lớn để không bị coi là rỗng
USER = Identity(user_id=1, role=Role.USER, session_id="s")


class FakeClock:
    def __init__(self) -> None:
        self.at = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.at

    def advance(self, **kwargs: float) -> None:
        self.at += timedelta(**kwargs)


class FakeGateway:
    def __init__(self, *, delay: float = 0.0, fail_times: int = 0, failure: CallStatus = CallStatus.ERROR):
        self.calls: list[tuple[str, str, Decimal]] = []
        self.delay = delay
        self.fail_times = fail_times
        self.failure = failure
        self.audio = AUDIO

    async def synthesize(self, text: str, voice: str, rate: Decimal) -> bytes:
        self.calls.append((text, voice, rate))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise TtsUnavailableError(self.failure, "FAKE")
        return self.audio


class FakeCache:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, Decimal], tuple[int, bytes | None]] = {}
        self.stores = 0
        self._next_id = 1

    async def find(self, text_sha256: str, voice: str, rate: Decimal) -> CachedAudio | None:
        row = self.rows.get((text_sha256, voice, rate))
        return CachedAudio(row[0], f"audio/{row[0]}.mp3") if row else None

    async def read(self, cached: CachedAudio) -> bytes:
        for cache_id, data in self.rows.values():
            if cache_id == cached.cache_id:
                if data is None:
                    raise NotFoundError("Tệp không còn tồn tại")
                return data
        raise NotFoundError()

    async def store(
        self, text_sha256: str, voice: str, rate: Decimal, audio: bytes, now: datetime
    ) -> CachedAudio:
        self.stores += 1
        key = (text_sha256, voice, rate)
        cache_id = self.rows[key][0] if key in self.rows else self._next_id
        self._next_id = max(self._next_id, cache_id) + 1
        self.rows[key] = (cache_id, audio)
        return CachedAudio(cache_id, f"audio/{cache_id}.mp3")


class FakeCallLog:
    def __init__(self) -> None:
        self.entries: list[ExternalCallEntry] = []

    async def record(self, entry: ExternalCallEntry) -> None:
        self.entries.append(entry)


class FakeVoices:
    def __init__(self, voice: str | None = None) -> None:
        self.voice = voice

    async def get_voice(self, identity: Identity) -> str | None:
        return self.voice


class Harness:
    def __init__(self, gateway: FakeGateway | None = None, *, enabled: bool = True) -> None:
        self.gateway = gateway or FakeGateway()
        self.cache = FakeCache()
        self.call_log = FakeCallLog()
        self.voices = FakeVoices()
        self.flight = SingleFlight()
        self.clock = FakeClock()
        self.sleeps: list[float] = []
        self.limiter = FailureLimiter(timedelta(minutes=10), self.clock)

        async def fake_sleep(seconds: float) -> None:
            self.sleeps.append(seconds)

        self.use_case = SynthesizeSpeechUseCase(
            gateway=self.gateway,
            cache=self.cache,
            call_log=self.call_log,
            voices=self.voices,
            flight=self.flight,
            guest_limiter=self.limiter,
            clock=self.clock,
            policy=TtsPolicy(enabled=enabled, guest_max_requests=3),
            sleep=fake_sleep,
        )
