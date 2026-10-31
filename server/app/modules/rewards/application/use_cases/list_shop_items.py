from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import ShopItemView
from app.modules.rewards.application.ports import RewardsUnitOfWork


class ListShopItemsUseCase:
    """F17.07 - Các món đang bán kèm giá, số lượt còn lại, cờ đã sở hữu khung và cờ đủ xu (US-NH-98).

    Khung thưởng mùa và khung VIP không bao giờ có trong cửa hàng: admin không thêm được (F17.09).
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity) -> list[ShopItemView]:
        user_id = identity.user_id
        async with self._uow_factory() as uow:
            items = await uow.shop.list_items(only_active=True)
            wallet = await uow.wallets.get_wallet(user_id)
            used = await uow.shop.count_redemptions_by_item(user_id)
            frames = {f.id: f for f in await uow.wallets.list_frames()}
            permanent = {f.frame_id for f in await uow.wallets.list_user_frames(user_id) if f.is_permanent}
        coins = wallet.coin_balance if wallet else 0
        views = []
        for item in items:
            limit = item.per_user_limit
            views.append(
                ShopItemView(
                    item=item,
                    frame=frames.get(item.frame_id) if item.frame_id is not None else None,
                    remaining=None if limit is None else max(0, limit - used.get(item.id, 0)),
                    owned=item.frame_id is not None and item.frame_id in permanent,
                    affordable=coins >= item.price_coins,
                )
            )
        return views
