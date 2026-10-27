"""Giao diện (port) của M12 Thống kê."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, Protocol

from app.modules.auth.application.public import Identity
from app.modules.stats.application.dto import (
    ActivityTotals,
    ContentCounts,
    ImagingCounts,
    LearningFacts,
    SeriesReadingProgress,
    UserCounts,
    VocabCounts,
)
from app.modules.stats.domain.activity import ActivityDelta, DayActivity


class ActivityRepository(Protocol):
    """Mọi truy vấn lọc theo `user_id`."""

    async def add(self, user_id: int, day: date, delta: ActivityDelta, now: datetime) -> None:
        """Cộng dồn vào bộ đếm của ngày (tạo dòng nếu chưa có), nguyên tử."""
        ...

    async def between(self, user_id: int, start: date, end: date) -> list[DayActivity]:
        """Các ngày có dòng trong [start, end], cũ nhất trước."""
        ...

    async def study_days(self, user_id: int) -> list[date]:
        """Mọi ngày có học (có lượt ôn hoặc trang đọc) của người học."""
        ...

    async def lifetime_totals(self, user_id: int) -> ActivityDelta:
        """Tổng mọi bộ đếm từ trước tới nay."""
        ...

    async def system_totals(self, start: date, end: date) -> ActivityTotals:
        """Tổng của mọi người dùng trong [start, end] (F12.03)."""
        ...


class StatsUnitOfWork(Protocol):
    @property
    def activity(self) -> ActivityRepository: ...

    async def __aenter__(self) -> StatsUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...


class UserTimezoneSource(Protocol):
    async def timezone_of(self, identity: Identity, owner_id: int) -> str: ...


class LearningFactsSource(Protocol):
    """Số liệu hiện tại của M07/M08; M08 hiện thực."""

    async def facts(self, identity: Identity, user_id: int) -> LearningFacts: ...


class ReadingProgressSource(Protocol):
    """Tiến độ đọc từng truyện; M03 hiện thực."""

    async def series_progress(self, user_id: int, limit: int) -> Sequence[SeriesReadingProgress]: ...


class UserCountsSource(Protocol):
    async def user_counts(self, now: datetime) -> UserCounts: ...


class ContentCountsSource(Protocol):
    async def content_counts(self) -> ContentCounts: ...


class ImagingCountsSource(Protocol):
    async def imaging_counts(self) -> ImagingCounts: ...


class VocabCountsSource(Protocol):
    async def vocab_counts(self) -> VocabCounts: ...
