from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import LedgerPage, UnlockView, UserRewardsView
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.views import build_wallet_view


class GetUserRewardsUseCase:
    """F17.10 - Quản trị viên xem ví, VIP, truyện đã mở khóa, khung và sổ của một người (US-QT-18).

    Người dùng đích đã được kiểm tra tồn tại ở tầng api (`get_target_user_id`, 404 `USER_NOT_FOUND`).
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, actor: Identity, user_id: int, page: int, size: int) -> UserRewardsView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            wallet = await build_wallet_view(uow.wallets, user_id, self._clock.now())
            unlocks = await uow.unlocks.list_for_user(user_id)
            titles = await uow.series.titles([u.series_id for u in unlocks])
            catalog = {f.id: f for f in await uow.wallets.list_frames()}
            owned = await uow.wallets.list_user_frames(user_id)
            entries, total = await uow.wallets.list_ledger(user_id, None, (page - 1) * size, size)
        return UserRewardsView(
            wallet=wallet,
            unlocks=[UnlockView(u, titles.get(u.series_id)) for u in unlocks],
            frames=[(catalog[f.frame_id], f) for f in owned if f.frame_id in catalog],
            ledger=LedgerPage(entries, total),
        )
