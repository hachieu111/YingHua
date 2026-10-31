from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import QuestsToday
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.application.quests import quests_today
from app.modules.stats.application.public import local_date


class GetQuestsTodayUseCase:
    """F16.04 - 3 nhiệm vụ ngày kèm tiến độ (US-NH-85). Tính khi gọi từ `daily_activities` và sổ XP.

    Phần thưởng được trao tự động lúc F16.02 ghi sự kiện liên quan, không có nút nhận. "Hôm nay" theo múi giờ
    của người học.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> QuestsToday:
        async with self._uow_factory() as uow:
            profile = await uow.users.profile(identity.user_id)
            day = local_date(self._clock.now(), profile.timezone)
            return await quests_today(uow, identity.user_id, day)
