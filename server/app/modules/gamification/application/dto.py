"""DTO của M16 (đầu vào/ra của use case và port)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from app.modules.gamification.domain.blade_rules import BladeEvent
from app.modules.gamification.domain.entities import BladeItem, SeasonTier
from app.modules.gamification.domain.minigame_rules import WeakRadical


@dataclass(frozen=True, slots=True)
class UserProfile:
    """Phần cài đặt/hồ sơ của một người mà M16 cần (M01, M02)."""

    user_id: int
    timezone: str
    weekly_page_goal: int | None
    hsk_level: int | None
    show_on_leaderboard: bool
    display_name: str = ""
    avatar_file_id: int | None = None
    avatar_preset: str | None = None


@dataclass(frozen=True, slots=True)
class DayCounters:
    pages_read: int = 0
    reviews_count: int = 0


@dataclass(frozen=True, slots=True)
class RankedScore:
    """Một dòng đã xếp hạng (chưa có thông tin hiển thị)."""

    user_id: int
    rank: int
    score: int


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """Dòng bảng xếp hạng kèm thông tin hồ sơ công khai; không có email."""

    user_id: int
    rank: int
    score: int
    display_name: str
    avatar_file_id: int | None
    avatar_preset: str | None
    hsk_level: int | None
    show_on_leaderboard: bool


@dataclass(frozen=True, slots=True)
class LeaderboardTotals:
    learners: int
    pages_in_period: int
    season_xp: int


@dataclass(frozen=True, slots=True)
class BadgeView:
    code: str
    name: str
    tier: int
    style_key: str


@dataclass(frozen=True, slots=True)
class FrameView:
    code: str
    name: str
    style_key: str


@dataclass(frozen=True, slots=True)
class Notice:
    """Thông báo trong ứng dụng chờ gửi sau khi giao dịch thưởng đã lưu (F14.05)."""

    user_id: int
    kind: str  # giá trị của NotificationKind
    title: str
    body: str | None = None
    data: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QuestView:
    code: str
    name: str
    progress: int
    target: int
    xp: int
    completed: bool
    rewarded_at: datetime | None


@dataclass(frozen=True, slots=True)
class QuestsToday:
    day: date
    quests: list[QuestView]
    bonus_coins: int
    bonus_granted: bool

    @property
    def completed_count(self) -> int:
        return sum(1 for q in self.quests if q.completed)


@dataclass(frozen=True, slots=True)
class WeeklyGoalView:
    week_start: date
    goal: int  # giá trị người học đã đặt (hoặc mặc định)
    rewarded_goal: int  # mục tiêu dùng để thưởng (không thấp hơn mức tối thiểu)
    pages_read: int
    pages_left: int
    percent: int
    reward_xp: int
    reward_frame_code: str
    reward_frame_days: int
    rewarded_at: datetime | None


@dataclass(frozen=True, slots=True)
class MilestoneProgress:
    days: int
    days_left: int


@dataclass(frozen=True, slots=True)
class MeView:
    xp_today: int
    xp_season: int
    xp_total: int
    season_rank: int | None
    streak_current: int
    next_streak_milestone: MilestoneProgress | None
    equipped_badge: BadgeView | None


@dataclass(frozen=True, slots=True)
class WeeklyActivityDay:
    day: date
    xp: int


@dataclass(frozen=True, slots=True)
class WeeklyActivity:
    week_start: date
    days: list[WeeklyActivityDay]
    total: int


@dataclass(frozen=True, slots=True)
class BoardRow:
    rank: int | None
    display_name: str
    avatar_file_id: int | None
    avatar_preset: str | None
    hsk_level: int | None
    score: int
    unit: str
    badge: BadgeView | None
    frame: FrameView | None
    is_vip: bool
    is_me: bool
    anonymous: bool


@dataclass(frozen=True, slots=True)
class NextMilestone:
    rank: int
    xp_missing: int
    ratio: float


@dataclass(frozen=True, slots=True)
class LeaderboardView:
    items: list[BoardRow]
    total: int
    page: int
    size: int
    me: BoardRow
    me_hidden: bool
    next_milestone: NextMilestone | None
    summary: LeaderboardTotals


@dataclass(frozen=True, slots=True)
class TierInfo:
    tier: SeasonTier
    rank_from: int
    rank_to: int
    coins: int = 0
    tickets: int = 0
    vip_days: int = 0
    frame_code: str | None = None
    badge_code: str | None = None


@dataclass(frozen=True, slots=True)
class CurrentSeasonView:
    id: int
    number: int
    starts_at: datetime
    ends_at: datetime
    server_now: datetime
    seconds_left: int
    status: str
    finalizing_previous: bool
    tiers: list[TierInfo]
    min_xp: int
    my_rank: int | None
    my_xp: int
    my_tier: SeasonTier | None


@dataclass(frozen=True, slots=True)
class SeasonHistoryItem:
    season_number: int
    starts_at: datetime
    ends_at: datetime
    rank: int
    xp: int
    tier: SeasonTier
    reward_granted_at: datetime | None


@dataclass(frozen=True, slots=True)
class SeasonHistory:
    items: list[SeasonHistoryItem]
    total: int


@dataclass(frozen=True, slots=True)
class AchievementProgress:
    code: str
    name: str
    description: str
    style_key: str
    tier: int
    max_tier: int
    progress: int
    next_threshold: int | None
    thresholds: tuple[int, ...]
    unlocked_at: datetime | None
    equipped: bool


@dataclass(frozen=True, slots=True)
class EquippedBadge:
    code: str | None
    name: str | None
    tier: int | None
    style_key: str | None


@dataclass(frozen=True, slots=True)
class WeakRadicalsView:
    radicals: list[WeakRadical]
    fallback: bool
    message: str | None


@dataclass(frozen=True, slots=True)
class BuildRoundCommand:
    mode: str
    hsk_band: int | None
    radical: str | None


@dataclass(frozen=True, slots=True)
class RoundView:
    round_id: uuid.UUID
    mode: str
    hsk_band: int | None
    radical: str | None
    seconds: int
    lives: int
    items: list[BladeItem]


@dataclass(frozen=True, slots=True)
class SubmitRoundCommand:
    """Mã lượt, chuỗi sự kiện và số liệu trình duyệt đo; bộ mục, đáp án và điểm do máy chủ giữ/tính."""

    round_id: uuid.UUID
    events: list[BladeEvent]
    typos: int
    duration_ms: int


@dataclass(frozen=True, slots=True)
class MissedItem:
    text: str
    pinyin: str
    han_viet: str | None


@dataclass(frozen=True, slots=True)
class SessionResult:
    id: int
    mode: str
    hsk_band: int | None
    radical: str | None
    score: int
    correct: int
    wrong: int
    typos: int
    max_combo: int
    accuracy: float
    rank: str
    duration_ms: int
    xp_awarded: int
    is_best: bool
    missed: list[MissedItem]


@dataclass(frozen=True, slots=True)
class FinalizeReport:
    seasons_created: int = 0
    seasons_finalized: int = 0
    rewarded: dict[str, int] = field(default_factory=dict)
    failed: int = 0
    pending_seasons: int = 0

    def as_summary(self) -> dict[str, object]:
        return {
            "seasons_created": self.seasons_created,
            "seasons_finalized": self.seasons_finalized,
            "rewarded": dict(self.rewarded),
            "failed": self.failed,
            "pending_seasons": self.pending_seasons,
        }


@dataclass(frozen=True, slots=True)
class EvaluateReport:
    scanned: int = 0
    unlocked: int = 0
    failed: int = 0

    def as_summary(self) -> dict[str, int]:
        return {"scanned": self.scanned, "unlocked": self.unlocked, "failed": self.failed}
