"""Đánh giá và trao huy hiệu (F16.11). Huy hiệu đã mở khóa không bao giờ bị thu hồi."""

from __future__ import annotations

from datetime import datetime

from app.modules.gamification.application.dto import AchievementProgress, Notice
from app.modules.gamification.application.ports import GamificationStore
from app.modules.gamification.domain.achievement_rules import (
    RULE_METRICS,
    achievement_key,
    coins_for_tiers,
    next_threshold,
    tier_for_value,
)
from app.modules.gamification.domain.entities import (
    Achievement,
    AchievementMetric,
    AchievementSource,
    UserAchievement,
)
from app.modules.notifications.application.public import NotificationKind
from app.modules.rewards.application.public import LedgerReason, RewardBundle

_ROMAN = {1: "I", 2: "II", 3: "III"}


def _notice(user_id: int, achievement: Achievement, tier: int) -> Notice:
    return Notice(
        user_id,
        NotificationKind.ACHIEVEMENT_UNLOCKED.value,
        f"Mở khóa huy hiệu {achievement.name}",
        f"Bạn đạt cấp {_ROMAN.get(tier, tier)} của huy hiệu {achievement.name}.",
        {"achievement_code": achievement.code, "tier": tier},
    )


class AchievementEngine:
    def __init__(self, store: GamificationStore) -> None:
        self._store = store

    async def evaluate(
        self,
        user_id: int,
        timezone: str,
        metrics: frozenset[AchievementMetric] | None,
        now: datetime,
        notices: list[Notice],
    ) -> int:
        """Đánh giá huy hiệu theo luật thuộc `metrics` (None = tất cả). Trả số huy hiệu lên cấp."""
        wanted = RULE_METRICS if metrics is None else metrics & RULE_METRICS
        defs = [a for a in await self._store.achievements.list_active() if a.metric in wanted]
        if not defs:
            return 0
        values = await self._store.metrics.values(user_id, {a.metric for a in defs}, timezone)
        rows = await self._store.achievements.user_rows(user_id)
        upgraded = 0
        for achievement in defs:
            tier = tier_for_value(values.get(achievement.metric, 0), achievement.thresholds)
            current = rows[achievement.id].tier if achievement.id in rows else 0
            if tier > current:
                await self._raise_tier(
                    user_id, achievement, current, tier, AchievementSource.RULE, now, notices
                )
                upgraded += 1
        return upgraded

    async def award_season_badge(self, user_id: int, code: str, now: datetime, notices: list[Notice]) -> None:
        """Huy hiệu do thưởng mùa: cấp I nếu chưa có (đã có thì giữ nguyên, kể cả cấp cao hơn)."""
        achievement = await self._store.achievements.get_by_code(code)
        if achievement is None:
            return
        rows = await self._store.achievements.user_rows(user_id)
        if achievement.id in rows:
            return
        await self._raise_tier(user_id, achievement, 0, 1, AchievementSource.SEASON, now, notices)

    async def _raise_tier(
        self,
        user_id: int,
        achievement: Achievement,
        from_tier: int,
        to_tier: int,
        source: AchievementSource,
        now: datetime,
        notices: list[Notice],
    ) -> None:
        await self._store.achievements.upsert_tier(user_id, achievement.id, to_tier, source, now)
        for tier, coins in coins_for_tiers(achievement, from_tier, to_tier):
            await self._store.rewards.grant(
                user_id,
                RewardBundle(coins=coins),
                achievement_key(achievement.code, tier),
                LedgerReason.ACHIEVEMENT,
                now,
            )
        notices.append(_notice(user_id, achievement, to_tier))


def build_progress(achievement: Achievement, row: UserAchievement | None, value: int) -> AchievementProgress:
    tier = row.tier if row else 0
    return AchievementProgress(
        code=achievement.code,
        name=achievement.name,
        description=achievement.description,
        style_key=achievement.style_key,
        tier=tier,
        max_tier=len(achievement.thresholds),
        progress=value,
        next_threshold=next_threshold(achievement, tier),
        thresholds=achievement.thresholds,
        unlocked_at=row.unlocked_at if row else None,
        equipped=row.is_equipped if row else False,
    )
