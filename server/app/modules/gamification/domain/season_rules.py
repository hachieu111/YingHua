"""Mùa thi đua, bậc thưởng và khoảng thời gian của bảng xếp hạng (F16.07, F16.09, F16.10).

Mùa và bảng xếp hạng tuần/tháng tính theo giờ Việt Nam cho mọi người. Việt Nam không có giờ mùa hè nên dùng
độ lệch cố định UTC+7 (không phụ thuộc cơ sở dữ liệu múi giờ của hệ điều hành).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from app.modules.gamification.domain.entities import LeaderboardMetric, LeaderboardPeriod, SeasonTier

VN_TZ = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")
SEASON_DAYS = 7
SEASON_MIN_XP = 50  # điều kiện nhận thưởng mùa
SEASON_TOP_N = 50
LEADERBOARD_DEFAULT_SIZE = 50
LEADERBOARD_MAX_SIZE = 100
# Mốc thưởng phía trên mà dòng "Bạn" nhắm tới (F16.07 bước 6), từ thấp lên cao.
MILESTONE_RANKS: tuple[int, ...] = (50, 10, 3, 1)
SEASON_CATCHUP_WEEKS = 12  # chạy bù tối đa bấy nhiêu tuần gần nhất khi tạo mùa còn thiếu (F16.10)
ANONYMOUS_NAME = "Học viên ẩn danh"
HIDDEN_NOTE = "Bạn đang ẩn tên trên bảng xếp hạng"

_FAR_PAST = datetime(2000, 1, 1, tzinfo=timezone.utc)
_FAR_FUTURE = datetime(2999, 1, 1, tzinfo=timezone.utc)
_UNITS: dict[LeaderboardMetric, str] = {
    LeaderboardMetric.EXP: "XP",
    LeaderboardMetric.VOCAB: "từ",
    LeaderboardMetric.PAGES: "trang",
    LeaderboardMetric.STREAK: "ngày",
}


def vn_date(at: datetime) -> date:
    return at.astimezone(VN_TZ).date()


def season_bounds(at: datetime) -> tuple[datetime, datetime]:
    """[Thứ Hai 00:00, Thứ Hai kế tiếp 00:00) giờ Việt Nam chứa `at`, trả về dạng UTC."""
    local = at.astimezone(VN_TZ).date()
    monday = local - timedelta(days=local.weekday())
    start = datetime.combine(monday, time.min, VN_TZ)
    return start.astimezone(timezone.utc), (start + timedelta(days=SEASON_DAYS)).astimezone(timezone.utc)


def week_starts_between(start: datetime, end: datetime) -> list[datetime]:
    """Mọi mốc đầu mùa (UTC) của các tuần giờ Việt Nam chạm vào [start, end], từ cũ đến mới."""
    first, _ = season_bounds(start)
    out: list[datetime] = []
    cursor = first
    while cursor <= end:
        out.append(cursor)
        cursor += timedelta(days=SEASON_DAYS)
    return out


def tier_for_rank(rank: int) -> SeasonTier | None:
    if 1 <= rank <= 3:
        return SeasonTier.TOP3
    if 4 <= rank <= 10:
        return SeasonTier.TOP10
    if 11 <= rank <= SEASON_TOP_N:
        return SeasonTier.TOP50
    return None


def next_milestone_rank(my_rank: int | None) -> int | None:
    """Mốc thưởng gần nhất phía trên hạng hiện tại; chưa có hạng thì nhắm mốc thấp nhất (hạng 50)."""
    if my_rank is None:
        return MILESTONE_RANKS[0]
    return next((r for r in MILESTONE_RANKS if r < my_rank), None)


def xp_needed_for_milestone(my_xp: int, holder_xp: int | None) -> int:
    """XP còn thiếu để vượt người đang giữ mốc; chưa ai giữ mốc thì cần tối thiểu SEASON_MIN_XP."""
    threshold = SEASON_MIN_XP if holder_xp is None else max(holder_xp + 1, SEASON_MIN_XP)
    return max(0, threshold - my_xp)


def progress_ratio(my_xp: int, holder_xp: int | None) -> float:
    threshold = SEASON_MIN_XP if holder_xp is None else max(holder_xp + 1, SEASON_MIN_XP)
    return round(min(1.0, my_xp / threshold), 4)


@dataclass(frozen=True, slots=True)
class LeaderboardWindow:
    """Khoảng thời gian của một bảng: mốc thời điểm (cho sổ XP) và mốc ngày (cho bộ đếm theo ngày)."""

    start_at: datetime
    end_at: datetime  # loại trừ
    start_date: date
    end_date: date  # bao gồm
    today: date  # hôm nay theo giờ Việt Nam


def leaderboard_window(period: LeaderboardPeriod, now: datetime) -> LeaderboardWindow:
    today = vn_date(now)
    if period is LeaderboardPeriod.WEEK:
        start_at, end_at = season_bounds(now)
        return LeaderboardWindow(
            start_at, end_at, vn_date(start_at), vn_date(end_at) - timedelta(days=1), today
        )
    if period is LeaderboardPeriod.MONTH:
        first = today.replace(day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        return LeaderboardWindow(
            datetime.combine(first, time.min, VN_TZ).astimezone(timezone.utc),
            datetime.combine(nxt, time.min, VN_TZ).astimezone(timezone.utc),
            first,
            nxt - timedelta(days=1),
            today,
        )
    return LeaderboardWindow(_FAR_PAST, _FAR_FUTURE, date(2000, 1, 1), date(2999, 1, 1), today)


def metric_unit(metric: LeaderboardMetric) -> str:
    return _UNITS[metric]


def seconds_until(now: datetime, end: datetime) -> int:
    return max(0, int((end - now).total_seconds()))
