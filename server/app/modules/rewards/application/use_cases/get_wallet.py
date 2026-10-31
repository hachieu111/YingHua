from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import WalletView
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.views import build_wallet_view


class GetWalletUseCase:
    """F17.02 - Xem ví: số xu, số vé, trạng thái VIP và khung đang đeo (US-NH-93)."""

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> WalletView:
        async with self._uow_factory() as uow:
            return await build_wallet_view(uow.wallets, identity.user_id, self._clock.now())
