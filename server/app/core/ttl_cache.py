"""Bộ đệm một giá trị có hạn dùng, giữ trong bộ nhớ tiến trình (vd. danh sách giọng TTS khả dụng)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Generic, TypeVar

from app.core.clock import Clock

T = TypeVar("T")


class TtlCache(Generic[T]):
    """Một ô nhớ: `get` trả None khi chưa có hoặc hết hạn. Đơn luồng nên không cần khóa."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._value: T | None = None
        self._expires_at: datetime | None = None

    def get(self) -> T | None:
        if self._expires_at is None or self._clock.now() >= self._expires_at:
            return None
        return self._value

    def set(self, value: T, ttl: timedelta) -> None:
        self._value = value
        self._expires_at = self._clock.now() + ttl
