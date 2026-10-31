"""Quy tắc huy hiệu và thành tựu (F16.11, F16.12)."""

from __future__ import annotations

from app.core.learning_events import LearningSignal, LearningSource
from app.modules.gamification.domain.entities import Achievement, AchievementMetric

NIGHT_START_HOUR = 23  # trang đọc lần đầu trong khung 23:00-03:59 giờ địa phương
NIGHT_END_HOUR = 4  # loại trừ
HSK3_LEVEL = 3
HSK3_MASTERED_STABILITY_DAYS = 21.0
SEASON_TOP3_CODE = "top_scholar"
SEASON_TOP50_CODE = "seed_sower"

# Chỉ số rẻ để tính ngay sau sự kiện XP; chỉ số còn lại (vd. bong bóng đã tra) do tác vụ nền quét (F16.11).
EVENT_METRICS: dict[LearningSource, frozenset[AchievementMetric]] = {
    LearningSource.PAGE_READ: frozenset(
        {AchievementMetric.PAGES_READ, AchievementMetric.NIGHT_PAGES, AchievementMetric.STUDY_DAYS}
    ),
    LearningSource.WORD_SAVED: frozenset({AchievementMetric.WORDS_SAVED, AchievementMetric.HSK3_MASTERED}),
    LearningSource.QUIZ: frozenset({AchievementMetric.HSK3_MASTERED}),
    LearningSource.REVIEW: frozenset({AchievementMetric.HSK3_MASTERED}),  # thẻ vừa đạt S ≥ 21 ngày
}
# Hành động không sinh XP, đánh giá sau khi lưu (F16.11).
SIGNAL_METRICS: dict[LearningSignal, frozenset[AchievementMetric]] = {
    LearningSignal.VOCAB_MASTERED: frozenset({AchievementMetric.HSK3_MASTERED}),
    LearningSignal.BUBBLE_LOOKUP: frozenset({AchievementMetric.BUBBLE_LOOKUPS}),
}
RULE_METRICS: frozenset[AchievementMetric] = frozenset(AchievementMetric) - {AchievementMetric.SEASON_TOP3}


def tier_for_value(value: int, thresholds: tuple[int, ...]) -> int:
    """Cấp cao nhất đạt được (0 = chưa đạt). Ngưỡng tăng dần."""
    return sum(1 for t in thresholds if value >= t)


def coins_for_tiers(achievement: Achievement, from_tier: int, to_tier: int) -> list[tuple[int, int]]:
    """Xu của từng cấp mới đạt, dạng (cấp, số xu), chỉ các cấp có xu > 0. Một lần có thể vượt nhiều cấp."""
    out: list[tuple[int, int]] = []
    for tier in range(from_tier + 1, to_tier + 1):
        coins = achievement.coin_rewards[tier - 1] if tier - 1 < len(achievement.coin_rewards) else 0
        if coins > 0:
            out.append((tier, coins))
    return out


def next_threshold(achievement: Achievement, tier: int) -> int | None:
    """Ngưỡng của cấp kế tiếp; None khi đã đạt cấp cao nhất."""
    return achievement.thresholds[tier] if tier < len(achievement.thresholds) else None


def achievement_key(code: str, tier: int) -> str:
    return f"achievement:{code}:{tier}"
