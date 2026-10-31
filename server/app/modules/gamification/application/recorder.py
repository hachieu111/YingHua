"""F16.02 - Ghi nhận XP từ hoạt động học và kích hoạt thưởng phụ (nhiệm vụ, mục tiêu tuần, mốc chuỗi...).

Chạy TRONG giao dịch của module nguồn (cùng phiên): hành động học và XP cùng lưu hoặc cùng hủy. Khóa tư vấn
theo người dùng làm hai yêu cầu đồng thời của một người không vượt trần ngày.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.core.learning_events import LearningEvent, LearningSource
from app.modules.gamification.application.achievement_engine import AchievementEngine
from app.modules.gamification.application.dto import Notice, UserProfile
from app.modules.gamification.application.ports import GamificationStore
from app.modules.gamification.application.quests import award_xp, evaluate_quests
from app.modules.gamification.domain.achievement_rules import EVENT_METRICS
from app.modules.gamification.domain.entities import NewXpEvent, XpSource
from app.modules.gamification.domain.xp_rules import (
    WEEKLY_GOAL_FRAME_CODE,
    WEEKLY_GOAL_FRAME_DAYS,
    WEEKLY_GOAL_XP,
    apply_caps,
    base_xp,
    reached_milestones,
    rewarded_weekly_goal,
    streak_ref,
    week_start,
    xp_source_of,
)
from app.modules.notifications.application.public import NotificationKind
from app.modules.rewards.application.public import (
    FrameGrant,
    FrameSource,
    LedgerReason,
    RewardBundle,
)
from app.modules.stats.application.public import compute_streak, local_date

_QUEST_TRIGGERS = frozenset({LearningSource.PAGE_READ, LearningSource.REVIEW, LearningSource.QUIZ})
_STREAK_TRIGGERS = frozenset({LearningSource.PAGE_READ, LearningSource.REVIEW})


class EventRecorder:
    def __init__(self, store: GamificationStore) -> None:
        self._store = store

    async def record(self, event: LearningEvent, notices: list[Notice]) -> int:
        """Ghi sự kiện XP; trả số XP thực nhận (0 nếu trùng, chạm trần hoặc không đủ điều kiện)."""
        base = base_xp(event)
        if base is None:
            return 0
        store = self._store
        source = xp_source_of(event.source)
        await store.xp.lock_user(event.user_id)
        if await store.xp.exists(event.user_id, source, event.ref):
            return 0
        profile = await store.users.profile(event.user_id)
        day = local_date(event.at, profile.timezone)
        capped = apply_caps(
            base,
            source,
            await store.xp.count_for_day(event.user_id, day, source),
            await store.xp.activity_xp_for_day(event.user_id, day),
        )
        inserted = await store.xp.insert_if_absent(
            NewXpEvent(event.user_id, source, event.ref, capped.amount, capped.capped, day, event.at)
        )
        if not inserted:
            return 0
        await self._follow_up(event, profile, day, notices)
        return capped.amount

    async def _follow_up(
        self, event: LearningEvent, profile: UserProfile, day: date, notices: list[Notice]
    ) -> None:
        uid, now, kind = event.user_id, event.at, event.source
        if kind in _QUEST_TRIGGERS:
            await evaluate_quests(self._store, uid, kind, day, now)
        if kind is LearningSource.PAGE_READ:
            await self._weekly_goal(profile, day, now)
        if kind in _STREAK_TRIGGERS:
            await self._streak(uid, day, now, notices)
        metrics = EVENT_METRICS.get(kind)
        if metrics:
            await AchievementEngine(self._store).evaluate(uid, profile.timezone, metrics, now, notices)

    async def _weekly_goal(self, profile: UserProfile, day: date, now: datetime) -> None:
        """F16.05: đạt mục tiêu tuần thì +150 XP và khung 7 ngày; mỗi tuần một lần (khóa = đầu tuần)."""
        uid = profile.user_id
        start = week_start(day)
        pages = await self._store.activity.pages_between(uid, start, start + timedelta(days=6))
        if pages < rewarded_weekly_goal(profile.weekly_page_goal):
            return
        if not await award_xp(
            self._store, uid, XpSource.WEEKLY_GOAL, start.isoformat(), WEEKLY_GOAL_XP, day, now
        ):
            return
        # Gói chỉ có khung không được ghi sổ nên M17 không chống trùng; khóa XP ở trên đã chống trùng cho M16.
        frame = FrameGrant(WEEKLY_GOAL_FRAME_CODE, FrameSource.WEEKLY_GOAL, days=WEEKLY_GOAL_FRAME_DAYS)
        await self._store.rewards.grant(
            uid, RewardBundle(frame=frame), f"weekly_goal:{start.isoformat()}", None, now
        )

    async def _streak(self, user_id: int, day: date, now: datetime, notices: list[Notice]) -> None:
        """F16.06: mỗi mốc ≤ chuỗi hiện tại được thưởng một lần mỗi chuỗi (khóa `<mốc>:<ngày bắt đầu>`)."""
        streak = compute_streak(await self._store.activity.study_days(user_id), day)
        if streak.current <= 0:
            return
        last_day = day if streak.active_today else day - timedelta(days=1)
        start = last_day - timedelta(days=streak.current - 1)
        for milestone in reached_milestones(streak.current):
            ref = streak_ref(milestone, start)
            if not await award_xp(
                self._store, user_id, XpSource.STREAK_MILESTONE, ref, milestone.xp, day, now
            ):
                continue
            await self._store.rewards.grant(
                user_id,
                RewardBundle(coins=milestone.coins, vip_days=milestone.vip_days),
                ref,
                LedgerReason.STREAK_MILESTONE,
                now,
            )
            notices.append(
                Notice(
                    user_id,
                    NotificationKind.STREAK_MILESTONE.value,
                    f"Chuỗi {milestone.days} ngày học liên tiếp!",
                    f"Bạn nhận +{milestone.xp} XP và +{milestone.coins} xu Sakura"
                    + (f", +{milestone.vip_days} ngày VIP." if milestone.vip_days else "."),
                    {"milestone": milestone.days, "xp": milestone.xp, "coins": milestone.coins},
                )
            )
