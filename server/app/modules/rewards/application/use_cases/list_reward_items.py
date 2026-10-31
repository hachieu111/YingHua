from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import AdminItemView
from app.modules.rewards.application.ports import RewardsUnitOfWork


class ListRewardItemsUseCase:
    """F17.09 - Danh mục đổi thưởng đầy đủ (kể cả món ngừng bán) cho quản trị viên (US-QT-17)."""

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity) -> list[AdminItemView]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            items = await uow.shop.list_items(only_active=False)
            frames = {f.id: f for f in await uow.wallets.list_frames()}
            locked = {i.id: await uow.shop.item_has_redemptions(i.id) for i in items}
        return [
            AdminItemView(i, frames.get(i.frame_id) if i.frame_id is not None else None, locked[i.id])
            for i in items
        ]
