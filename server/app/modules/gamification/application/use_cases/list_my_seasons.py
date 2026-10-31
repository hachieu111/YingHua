from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import SeasonHistory, SeasonHistoryItem
from app.modules.gamification.application.ports import GamificationUnitOfWork


class ListMySeasonsUseCase:
    """F16.09 - Kết quả các mùa đã chốt của người gọi (kỳ, hạng, XP, bậc, lúc nhận thưởng). Mới nhất trước."""

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, page: int, size: int) -> SeasonHistory:
        async with self._uow_factory() as uow:
            rows, total = await uow.seasons.results_of_user(identity.user_id, (page - 1) * size, size)
        items = [
            SeasonHistoryItem(
                r.season.number,
                r.season.starts_at,
                r.season.ends_at,
                r.result.rank,
                r.result.xp,
                r.result.tier,
                r.result.reward_granted_at,
            )
            for r in rows
        ]
        return SeasonHistory(items, total)
