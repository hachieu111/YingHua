from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import EquippedBadge
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.errors import AchievementLockedError, AchievementNotFoundError


class EquipAchievementUseCase:
    """F16.12 - Đeo (hoặc tháo, khi `code` là None) một huy hiệu đã mở khóa (US-NH-92).

    Mỗi người tối đa một huy hiệu đang đeo; bỏ cái cũ và đeo cái mới trong một giao dịch. Mã không tồn tại
    → 404 `ACHIEVEMENT_NOT_FOUND`; chưa mở khóa → 409 `ACHIEVEMENT_LOCKED`, huy hiệu đang đeo giữ nguyên.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, code: str | None) -> EquippedBadge:
        uid = identity.user_id
        async with self._uow_factory() as uow:
            if code is None:
                await uow.achievements.set_equipped(uid, None)
                await uow.commit()
                return EquippedBadge(None, None, None, None)
            achievement = await uow.achievements.get_by_code(code)
            if achievement is None:
                raise AchievementNotFoundError()
            row = (await uow.achievements.user_rows(uid)).get(achievement.id)
            if row is None:
                raise AchievementLockedError()
            await uow.achievements.set_equipped(uid, achievement.id)
            await uow.commit()
            return EquippedBadge(achievement.code, achievement.name, row.tier, achievement.style_key)
