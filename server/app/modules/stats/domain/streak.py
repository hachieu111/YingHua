"""Chuỗi ngày học (F12.02)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

STREAK_RULE_TEXT = (
    "Một ngày được tính là có học khi bạn ôn ít nhất một thẻ hoặc đọc ít nhất một trang mới. "
    "Chuỗi đếm số ngày liên tiếp tính tới hôm nay; nếu hôm nay bạn chưa học thì chuỗi vẫn được giữ "
    "đến hết ngày, bỏ lỡ trọn một ngày thì chuỗi về 0."
)


@dataclass(frozen=True, slots=True)
class StreakResult:
    current: int
    longest: int
    active_today: bool


def compute_streak(study_days: Iterable[date], today: date) -> StreakResult:
    """Chuỗi hiện tại, chuỗi dài nhất và hôm nay đã học chưa.

    Hôm nay chưa học thì chuỗi tính lùi từ hôm qua (còn cơ hội học tiếp trong ngày); không có hôm qua thì 0.
    Ngày trong tương lai (lệch đồng hồ) bị bỏ qua.
    """
    days = {d for d in study_days if d <= today}
    if not days:
        return StreakResult(0, 0, False)
    cursor = today if today in days else today - timedelta(days=1)
    current = 0
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    return StreakResult(current, _longest_run(days), today in days)


def _longest_run(days: set[date]) -> int:
    longest = 0
    for start in days:
        if start - timedelta(days=1) in days:
            continue  # chỉ bắt đầu đếm ở đầu mỗi đoạn liên tiếp
        length = 1
        while start + timedelta(days=length) in days:
            length += 1
        longest = max(longest, length)
    return longest
