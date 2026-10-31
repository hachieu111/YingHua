from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.gamification.application.achievement_engine import build_progress
from app.modules.gamification.application.dto import AchievementProgress
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.achievement_rules import RULE_METRICS
from app.modules.gamification.domain.entities import AchievementMetric


class ListAchievementsUseCase:
    """F16.11 - Mọi huy hiệu đang dùng kèm cấp đã đạt, ngưỡng cấp kế tiếp, tiến độ, trạng thái đeo (US-NH-91).

    Tiến độ tính khi gọi; trạng thái mở khóa đọc từ bảng (có thể trễ tối đa 60 phút với chỉ số không sinh XP).
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity) -> list[AchievementProgress]:
        uid = identity.user_id
        async with self._uow_factory() as uow:
            profile = await uow.users.profile(uid)
            definitions = await uow.achievements.list_active()
            rows = await uow.achievements.user_rows(uid)
            wanted = {a.metric for a in definitions} & RULE_METRICS
            values = await uow.metrics.values(uid, wanted, profile.timezone)
        out: list[AchievementProgress] = []
        for a in definitions:
            row = rows.get(a.id)
            if a.metric is AchievementMetric.SEASON_TOP3:
                value = 1 if row else 0
            else:
                value = values.get(a.metric, 0)
            out.append(build_progress(a, row, value))
        return out
