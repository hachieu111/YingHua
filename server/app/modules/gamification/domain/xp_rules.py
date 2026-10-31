"""Quy tắc XP, nhiệm vụ ngày, mục tiêu tuần và mốc chuỗi ngày (F16.02, F16.04, F16.05, F16.06).

Mọi hằng số nghiệp vụ nằm ở đây (không "số ma thuật" rải rác). Hàm thuần: không đọc giờ hệ thống.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.core.learning_events import LearningEvent, LearningSource
from app.modules.gamification.domain.entities import XpSource

# --- Bảng XP (F16.02) -------------------------------------------------------------------------------------
XP_PER_PAGE = 2
XP_PER_REVIEW = 1
XP_PER_NEW_WORD = 3
QUIZ_BASE_XP = 10
QUIZ_MAX_XP = 20
MINIGAME_MAX_XP = 10
MINIGAME_SCORE_DIVISOR = 2

ACTIVITY_SOURCES: frozenset[XpSource] = frozenset(
    {XpSource.PAGE_READ, XpSource.REVIEW, XpSource.WORD_SAVED, XpSource.QUIZ, XpSource.MINIGAME}
)
# Trần số sự kiện mỗi nguồn mỗi ngày (theo múi giờ người học).
DAILY_EVENT_CAPS: dict[XpSource, int] = {
    XpSource.PAGE_READ: 100,
    XpSource.REVIEW: 200,
    XpSource.WORD_SAVED: 50,
    XpSource.QUIZ: 5,
    XpSource.MINIGAME: 5,
}
DAILY_XP_CAP = 300  # trần chung của các nguồn trong ACTIVITY_SOURCES

_SOURCE_MAP: dict[LearningSource, XpSource] = {
    LearningSource.PAGE_READ: XpSource.PAGE_READ,
    LearningSource.REVIEW: XpSource.REVIEW,
    LearningSource.WORD_SAVED: XpSource.WORD_SAVED,
    LearningSource.QUIZ: XpSource.QUIZ,
    LearningSource.MINIGAME: XpSource.MINIGAME,
}


def xp_source_of(source: LearningSource) -> XpSource:
    return _SOURCE_MAP[source]


def base_xp(event: LearningEvent) -> int | None:
    """XP gốc của sự kiện trước khi áp trần. None = không tạo sự kiện XP.

    Bài kiểm tra trả lời dưới một nửa số câu không tạo sự kiện (chống nộp bài trống để lấy thưởng).
    """
    match event.source:
        case LearningSource.PAGE_READ:
            return XP_PER_PAGE
        case LearningSource.REVIEW:
            return XP_PER_REVIEW
        case LearningSource.WORD_SAVED:
            return XP_PER_NEW_WORD
        case LearningSource.QUIZ:
            if event.total <= 0 or event.answered * 2 < event.total:
                return None
            return min(QUIZ_MAX_XP, QUIZ_BASE_XP + max(0, event.value))
        case LearningSource.MINIGAME:
            return min(MINIGAME_MAX_XP, max(0, event.value) // MINIGAME_SCORE_DIVISOR)
    return None


@dataclass(frozen=True, slots=True)
class CappedXp:
    amount: int
    capped: bool


def apply_caps(base: int, source: XpSource, events_today: int, activity_xp_today: int) -> CappedXp:
    """Áp trần riêng của nguồn (số sự kiện) và trần chung của ngày; phần vượt bị cắt, sự kiện vẫn được ghi."""
    if events_today >= DAILY_EVENT_CAPS[source]:
        return CappedXp(0, True)
    remaining = max(0, DAILY_XP_CAP - activity_xp_today)
    amount = min(base, remaining)
    return CappedXp(amount, amount < base)


# --- Nhiệm vụ ngày (F16.04) -------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class QuestDef:
    code: str
    name: str
    target: int
    xp: int
    trigger: LearningSource  # nguồn sự kiện làm tiến độ nhiệm vụ này thay đổi


QUESTS: tuple[QuestDef, ...] = (
    QuestDef("read_pages", "Đọc 2 trang truyện mới", 2, 20, LearningSource.PAGE_READ),
    QuestDef("review_cards", "Lật 15 thẻ Flashcard", 15, 15, LearningSource.REVIEW),
    QuestDef("take_quiz", "Làm 1 bài kiểm tra từ HSK", 1, 30, LearningSource.QUIZ),
)
QUEST_ALL_BONUS_COINS = 20


def quest_ref(code: str, day: date) -> str:
    return f"{code}:{day.isoformat()}"


def quests_all_key(day: date) -> str:
    return f"quests_all:{day.isoformat()}"


# --- Mục tiêu tuần (F16.05) -------------------------------------------------------------------------------
DEFAULT_WEEKLY_PAGE_GOAL = 20
MIN_REWARDED_WEEKLY_GOAL = 10  # đặt mục tiêu thấp hơn vẫn hiển thị đúng nhưng chỉ thưởng khi đọc từ 10 trang
WEEKLY_GOAL_XP = 150
WEEKLY_GOAL_FRAME_CODE = "sakura_gold"
WEEKLY_GOAL_FRAME_DAYS = 7


def week_start(day: date) -> date:
    """Thứ Hai của tuần chứa `day`."""
    return day - timedelta(days=day.weekday())


def rewarded_weekly_goal(goal: int | None) -> int:
    return max(goal if goal is not None else DEFAULT_WEEKLY_PAGE_GOAL, MIN_REWARDED_WEEKLY_GOAL)


# --- Mốc chuỗi ngày (F16.06) ------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class StreakMilestone:
    days: int
    xp: int
    coins: int
    vip_days: int


STREAK_MILESTONES: tuple[StreakMilestone, ...] = (
    StreakMilestone(7, 50, 50, 0),
    StreakMilestone(30, 200, 200, 3),
    StreakMilestone(100, 500, 500, 7),
)


def streak_ref(milestone: StreakMilestone, streak_start: date) -> str:
    return f"{milestone.days}:{streak_start.isoformat()}"


def reached_milestones(current_streak: int) -> list[StreakMilestone]:
    return [m for m in STREAK_MILESTONES if m.days <= current_streak]


def next_milestone(current_streak: int) -> StreakMilestone | None:
    return next((m for m in STREAK_MILESTONES if m.days > current_streak), None)
