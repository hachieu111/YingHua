from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.auth.application.public import Identity


@dataclass(frozen=True, slots=True)
class SynthesizeCommand:
    text: str
    identity: Identity | None  # None = Khách
    client_key: str  # địa chỉ máy khách, dùng giới hạn tần suất của Khách
    rate: Decimal | None = None
    voice: str | None = None


@dataclass(frozen=True, slots=True)
class SpeechAudio:
    audio: bytes
    voice: str
    rate: Decimal
    voice_fallback: bool  # giọng yêu cầu không khả dụng nên đã dùng giọng mặc định
    cache_hit: bool
