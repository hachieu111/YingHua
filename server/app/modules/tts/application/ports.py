from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.modules.auth.application.public import Identity
from app.modules.tts.domain.value_objects import CallStatus
from app.modules.tts.domain.voices import VoiceInfo


class TtsGateway(Protocol):
    async def synthesize(self, text: str, voice: str, rate: Decimal) -> bytes:
        """Một lần gọi dịch vụ TTS. Lỗi/hết thời gian -> TtsUnavailableError (không để lộ lỗi thư viện)."""
        ...


@dataclass(frozen=True, slots=True)
class CachedAudio:
    cache_id: int
    storage_key: str


class TtsCacheRepository(Protocol):
    async def find(self, text_sha256: str, voice: str, rate: Decimal) -> CachedAudio | None: ...

    async def read(self, cached: CachedAudio) -> bytes:
        """Raise NotFoundError nếu tệp trong kho đã mất."""
        ...

    async def store(
        self, text_sha256: str, voice: str, rate: Decimal, audio: bytes, now: datetime
    ) -> CachedAudio:
        """Ghi tệp + dòng bộ đệm; đã có dòng cùng khóa (hỏng/mất tệp) thì thay bằng bản mới."""
        ...


@dataclass(frozen=True, slots=True)
class ExternalCallEntry:
    """Một dòng nhật ký; cố ý không có nội dung văn bản hay thông tin người dùng."""

    provider: str
    operation: str
    status: CallStatus
    latency_ms: int
    error_code: str | None = None


class ExternalCallLog(Protocol):
    async def record(self, entry: ExternalCallEntry) -> None: ...


class VoicePreferences(Protocol):
    async def get_voice(self, identity: Identity) -> str | None:
        """Giọng đọc trong cài đặt cá nhân (F02.03); None nếu chưa chọn."""
        ...


class VoiceCatalog(Protocol):
    async def list_voices(self) -> list[VoiceInfo]:
        """Giọng tiếng Trung đang khả dụng của dịch vụ. Lỗi/hết thời gian -> TtsUnavailableError."""
        ...
