"""Nguồn thời gian — inject vào use case để test được FSRS, hạn token, hạn lưu file."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Thời điểm hiện tại, luôn có múi giờ UTC."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
