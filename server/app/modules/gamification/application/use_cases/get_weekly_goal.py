from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import WeeklyGoalView
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.entities import XpSource
from app.modules.gamification.domain.xp_rules import (
    DEFAULT_WEEKLY_PAGE_GOAL,
    WEEKLY_GOAL_FRAME_CODE,
    WEEKLY_GOAL_FRAME_DAYS,
    WEEKLY_GOAL_XP,
    rewarded_weekly_goal,
    week_start,
)
from app.modules.stats.application.public import local_date


class GetWeeklyGoalUseCase:
    """F16.05 - Mục tiêu tuần: mục tiêu đã đặt (mặc định 20 trang), số trang đã đọc từ Thứ Hai tới nay, phần
    thưởng và trạng thái đã thưởng (US-NH-86).

    Mục tiêu dưới 10 trang vẫn hiển thị đúng số đã đặt, nhưng thưởng chỉ trao khi đọc từ 10 trang trở lên.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> WeeklyGoalView:
        uid = identity.user_id
        async with self._uow_factory() as uow:
            profile = await uow.users.profile(uid)
            start = week_start(local_date(self._clock.now(), profile.timezone))
            pages = await uow.activity.pages_between(uid, start, start + timedelta(days=6))
            rewarded = await uow.xp.rewarded_at(uid, XpSource.WEEKLY_GOAL, [start.isoformat()])
        goal = profile.weekly_page_goal or DEFAULT_WEEKLY_PAGE_GOAL
        return WeeklyGoalView(
            week_start=start,
            goal=goal,
            rewarded_goal=rewarded_weekly_goal(profile.weekly_page_goal),
            pages_read=pages,
            pages_left=max(0, goal - pages),
            percent=min(100, pages * 100 // goal),
            reward_xp=WEEKLY_GOAL_XP,
            reward_frame_code=WEEKLY_GOAL_FRAME_CODE,
            reward_frame_days=WEEKLY_GOAL_FRAME_DAYS,
            rewarded_at=rewarded.get(start.isoformat()),
        )
