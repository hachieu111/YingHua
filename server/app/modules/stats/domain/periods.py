"""Chia khoảng thời gian cho biểu đồ hoạt động (F12.01)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from app.core.errors import InvalidInputError
from app.modules.stats.domain.activity import ActivityDelta, DayActivity

COMPARISON_DAYS = 7
MAX_POINTS = {"day": 90, "week": 52, "month": 24}


class Granularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True, slots=True)
class PeriodActivity:
    """Tổng hoạt động trong [start, end] (gồm cả hai đầu)."""

    start: date
    end: date
    reviews_count: int = 0
    pages_read: int = 0
    words_saved: int = 0
    quizzes_done: int = 0
    study_seconds: int = 0


def parse_granularity(value: str) -> Granularity:
    try:
        return Granularity(value)
    except ValueError as exc:
        raise InvalidInputError(
            "Chỉ hỗ trợ thống kê theo ngày, tuần hoặc tháng", details={"field": "granularity"}
        ) from exc


def check_count(granularity: Granularity, count: int) -> int:
    limit = MAX_POINTS[granularity.value]
    if not 1 <= count <= limit:
        raise InvalidInputError(f"Số mốc phải từ 1 đến {limit}", details={"field": "count"})
    return count


def _month_start(day: date, back: int) -> date:
    index = day.year * 12 + (day.month - 1) - back
    return date(index // 12, index % 12 + 1, 1)


def period_ranges(granularity: Granularity, today: date, count: int) -> list[tuple[date, date]]:
    """`count` khoảng liên tiếp kết thúc ở khoảng chứa `today`, cũ nhất trước. Tuần bắt đầu từ thứ Hai."""
    if granularity is Granularity.DAY:
        return [(today - timedelta(days=n), today - timedelta(days=n)) for n in range(count - 1, -1, -1)]
    if granularity is Granularity.WEEK:
        monday = today - timedelta(days=today.weekday())
        starts = [monday - timedelta(weeks=n) for n in range(count - 1, -1, -1)]
        return [(s, s + timedelta(days=6)) for s in starts]
    result: list[tuple[date, date]] = []
    for n in range(count - 1, -1, -1):
        start = _month_start(today, n)
        result.append((start, _month_start(today, n - 1) - timedelta(days=1)))
    return result


def sum_period(days: Sequence[DayActivity], start: date, end: date) -> PeriodActivity:
    in_range = [d for d in days if start <= d.day <= end]
    return PeriodActivity(
        start,
        end,
        reviews_count=sum(d.reviews_count for d in in_range),
        pages_read=sum(d.pages_read for d in in_range),
        words_saved=sum(d.words_saved for d in in_range),
        quizzes_done=sum(d.quizzes_done for d in in_range),
        study_seconds=sum(d.study_seconds for d in in_range),
    )


def aggregate(days: Sequence[DayActivity], ranges: Sequence[tuple[date, date]]) -> list[PeriodActivity]:
    return [sum_period(days, start, end) for start, end in ranges]


def difference(current: PeriodActivity, previous: PeriodActivity) -> ActivityDelta:
    """Chênh lệch (hiện tại trừ trước đó) từng bộ đếm; có thể âm."""
    return ActivityDelta(
        reviews_count=current.reviews_count - previous.reviews_count,
        pages_read=current.pages_read - previous.pages_read,
        words_saved=current.words_saved - previous.words_saved,
        quizzes_done=current.quizzes_done - previous.quizzes_done,
        study_seconds=current.study_seconds - previous.study_seconds,
    )
