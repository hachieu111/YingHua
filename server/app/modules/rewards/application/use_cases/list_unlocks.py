from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import UnlockView
from app.modules.rewards.application.ports import RewardsUnitOfWork


class ListUnlocksUseCase:
    """F17.06 - Các truyện VIP người gọi đã mở khóa bằng vé, mới nhất trước."""

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity) -> list[UnlockView]:
        async with self._uow_factory() as uow:
            unlocks = await uow.unlocks.list_for_user(identity.user_id)
            titles = await uow.series.titles([u.series_id for u in unlocks])
        return [UnlockView(u, titles.get(u.series_id)) for u in unlocks]
