from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import CurrentSeasonView
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.application.season_rewards import tier_infos
from app.modules.gamification.domain.entities import LeaderboardMetric, LeaderboardPeriod
from app.modules.gamification.domain.season_rules import (
    SEASON_MIN_XP,
    leaderboard_window,
    season_bounds,
    seconds_until,
    tier_for_rank,
)


class GetCurrentSeasonUseCase:
    """F16.09 - Mùa thi đua hiện hành: số kỳ, mốc bắt đầu/kết thúc (UTC), giờ máy chủ để đếm ngược, ba bậc
    thưởng, hạng và XP mùa của người gọi (US-NH-90).

    Chưa có mùa chứa thời điểm hiện tại thì tạo mùa của tuần này với số kỳ = lớn nhất + 1; hai yêu cầu cùng
    chỉ ra một mùa (khóa tư vấn + ràng buộc duy nhất theo `starts_at`).
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> CurrentSeasonView:
        now = self._clock.now()
        window = leaderboard_window(LeaderboardPeriod.WEEK, now)
        async with self._uow_factory() as uow:
            season = await uow.seasons.get_containing(now)
            if season is None:
                season, _ = await uow.seasons.ensure(*season_bounds(now), now)
                await uow.commit()
            mine = await uow.leaderboard.rank_of(LeaderboardMetric.EXP, window, identity.user_id)
            pending_previous = await uow.seasons.has_unfinished_ended(now)
        my_xp = mine.score if mine else 0
        eligible = mine is not None and my_xp >= SEASON_MIN_XP
        return CurrentSeasonView(
            id=season.id,
            number=season.number,
            starts_at=season.starts_at,
            ends_at=season.ends_at,
            server_now=now,
            seconds_left=seconds_until(now, season.ends_at),
            status=season.status.value,
            finalizing_previous=pending_previous,
            tiers=tier_infos(),
            min_xp=SEASON_MIN_XP,
            my_rank=mine.rank if mine else None,
            my_xp=my_xp,
            my_tier=tier_for_rank(mine.rank) if mine is not None and eligible else None,
        )
