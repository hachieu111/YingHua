from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.entities import BladeBest


class GetBladeBestUseCase:
    """F16.01 - Kỷ lục "Gõ pinyin chém chữ" của chính người gọi theo từng cấp HSK / chế độ bộ thủ yếu."""

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity) -> list[BladeBest]:
        async with self._uow_factory() as uow:
            return await uow.minigames.best_records(identity.user_id)
