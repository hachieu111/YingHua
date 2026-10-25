"""Giới hạn số lần thất bại theo khóa (email, IP) trong một cửa sổ thời gian.

Lưu trong bộ nhớ của tiến trình API: đủ cho một máy chủ; nhiều tiến trình cần chuyển sang kho dùng chung.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.clock import Clock


class FailureLimiter:
    def __init__(self, window: timedelta, clock: Clock) -> None:
        self._window = window
        self._clock = clock
        self._failures: dict[str, list[datetime]] = {}

    def _recent(self, key: str) -> list[datetime]:
        cutoff = self._clock.now() - self._window
        recent = [at for at in self._failures.get(key, []) if at > cutoff]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def is_blocked(self, key: str, max_attempts: int) -> bool:
        return len(self._recent(key)) >= max_attempts

    def record_failure(self, key: str) -> None:
        self._recent(key)  # dọn bản ghi đã quá hạn của khóa này
        self._failures.setdefault(key, []).append(self._clock.now())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
