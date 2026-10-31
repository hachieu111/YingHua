from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import MeView, MilestoneProgress
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.entities import LeaderboardMetric, LeaderboardPeriod
from app.modules.gamification.domain.season_rules import leaderboard_window
from app.modules.gamification.domain.xp_rules import next_milestone
from app.modules.stats.application.public import compute_streak, local_date


class GetMyGamificationUseCase:
    """F16.03 - XP hôm nay, XP mùa, tổng XP, hạng mùa, mốc chuỗi kế tiếp và huy hiệu đang đeo (US-NH-84).

    Chỉ dữ liệu của chính người gọi. Người mới: mọi số bằng 0, hạng rỗng. Quản trị viên được xếp hạng như
    Người học (người dùng chốt 30/10/2026).
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> MeView:
        uid, now = identity.user_id, self._clock.now()
        window = leaderboard_window(LeaderboardPeriod.WEEK, now)
        async with self._uow_factory() as uow:
            profile = await uow.users.profile(uid)
            day = local_date(now, profile.timezone)
            ranked = await uow.leaderboard.rank_of(LeaderboardMetric.EXP, window, uid)
            streak = compute_streak(await uow.activity.study_days(uid), day)
            badge = (await uow.achievements.equipped_for([uid])).get(uid)
            milestone = next_milestone(streak.current)
            return MeView(
                xp_today=await uow.xp.xp_for_day(uid, day),
                xp_season=await uow.xp.xp_between(uid, window.start_at, window.end_at),
                xp_total=await uow.xp.xp_total(uid),
                season_rank=ranked.rank if ranked else None,
                streak_current=streak.current,
                next_streak_milestone=(
                    MilestoneProgress(milestone.days, milestone.days - streak.current) if milestone else None
                ),
                equipped_badge=badge,
            )
