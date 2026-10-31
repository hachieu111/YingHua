from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import WeeklyActivity, WeeklyActivityDay
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.season_rules import SEASON_DAYS, season_bounds, vn_date


class GetWeeklyActivityUseCase:
    """F16.03 - "Hoạt động tuần của bạn": XP từng ngày Thứ Hai -> Chủ Nhật của tuần mùa hiện hành (giờ VN).

    Luôn trả đủ 7 ô (ô không có XP bằng 0). Người mới không lỗi.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> WeeklyActivity:
        start_at, end_at = season_bounds(self._clock.now())
        async with self._uow_factory() as uow:
            by_day = await uow.xp.xp_by_vn_day(identity.user_id, start_at, end_at)
        monday = vn_date(start_at)
        days = [
            WeeklyActivityDay(monday + timedelta(days=i), by_day.get(monday + timedelta(days=i), 0))
            for i in range(SEASON_DAYS)
        ]
        return WeeklyActivity(monday, days, sum(d.xp for d in days))
