"""Hoạt động học theo ngày (M12) — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Một lượt ôn bị treo máy lâu không được làm phồng thời gian học; 5 phút cho một thẻ là quá đủ.
MAX_STUDY_SECONDS_PER_REVIEW = 300
MAX_STUDY_MS_PER_REVIEW = MAX_STUDY_SECONDS_PER_REVIEW * 1000


@dataclass(frozen=True, slots=True)
class ActivityDelta:
    """Số gia của một hành động học; mỗi hành động chỉ đặt các trường liên quan."""

    reviews_count: int = 0
    pages_read: int = 0
    words_saved: int = 0
    quizzes_done: int = 0
    study_seconds: int = 0


@dataclass(frozen=True, slots=True)
class DayActivity:
    """Bộ đếm của một ngày theo múi giờ người học."""

    day: date
    reviews_count: int = 0
    pages_read: int = 0
    words_saved: int = 0
    quizzes_done: int = 0
    study_seconds: int = 0

    @property
    def is_study_day(self) -> bool:
        """F12.02: ngày có học = có ít nhất một lượt ôn hoặc mở một trang đọc."""
        return self.reviews_count > 0 or self.pages_read > 0


def resolve_timezone(name: str | None) -> timezone | ZoneInfo:
    """Múi giờ người học; tên sai hoặc thiếu → UTC."""
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return timezone.utc


def local_date(now: datetime, tz_name: str | None) -> date:
    """Ngày hiện tại theo múi giờ người học (F12.02: mỗi ngày tính một lần theo múi giờ của họ)."""
    return now.astimezone(resolve_timezone(tz_name)).date()


def study_seconds_from_ms(duration_ms: int | None) -> int:
    """Thời gian học của một lượt ôn, làm tròn tới giây và chặn trần. Backfill dùng cùng công thức."""
    if duration_ms is None or duration_ms <= 0:
        return 0
    return (min(duration_ms, MAX_STUDY_MS_PER_REVIEW) + 500) // 1000
