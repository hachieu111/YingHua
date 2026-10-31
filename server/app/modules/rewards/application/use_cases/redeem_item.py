from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import GrantCommand, RedeemCommand, RedemptionResult
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.views import build_wallet_view
from app.modules.rewards.domain.entities import (
    FrameGrant,
    FrameSource,
    ItemKind,
    LedgerReason,
    RewardBundle,
    RewardItem,
)
from app.modules.rewards.domain.errors import (
    FrameAlreadyOwnedError,
    RewardItemUnavailableError,
    RewardLimitReachedError,
)


class RedeemItemUseCase:
    """F17.07 - Đổi xu lấy ngày VIP, vé hoặc khung avatar (US-NH-98).

    Một giao dịch: khóa ví; kiểm món đang bán, giới hạn mỗi người, khung chưa sở hữu vĩnh viễn, đủ xu;
    trừ xu và trao món qua sổ (khóa chống trùng là mã yêu cầu); ghi lượt đổi kèm giá tại thời điểm đổi.
    Gửi lại cùng mã yêu cầu trả lại lượt đổi cũ, không trừ xu lần hai.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, command: RedeemCommand) -> RedemptionResult:
        now, user_id = self._clock.now(), identity.user_id
        async with self._uow_factory() as uow:
            await uow.wallets.lock_wallet(user_id, now)
            previous = await uow.shop.get_redemption(user_id, command.request_id)
            if previous is not None:
                item = await uow.shop.get_item(previous.item_id)
                if item is not None:
                    return RedemptionResult(
                        previous, item, await build_wallet_view(uow.wallets, user_id, now)
                    )
            item = await uow.shop.get_item(command.item_id)
            if item is None or not item.is_active:
                raise RewardItemUnavailableError()
            await self._check_limit(uow, user_id, item)
            bundle = await self._bundle_for(uow, user_id, item)
            ledger_command = GrantCommand(user_id, bundle, str(command.request_id), LedgerReason.REDEMPTION)
            await RewardLedger(uow.wallets).apply(ledger_command, now)
            redemption = await uow.shop.add_redemption(
                user_id, item.id, item.price_coins, command.request_id, now
            )
            view = await build_wallet_view(uow.wallets, user_id, now)
            await uow.commit()
        return RedemptionResult(redemption, item, view)

    @staticmethod
    async def _check_limit(uow: RewardsUnitOfWork, user_id: int, item: RewardItem) -> None:
        if item.per_user_limit is None:
            return
        used = (await uow.shop.count_redemptions_by_item(user_id)).get(item.id, 0)
        if used >= item.per_user_limit:
            raise RewardLimitReachedError(details={"limit": item.per_user_limit})

    @staticmethod
    async def _bundle_for(uow: RewardsUnitOfWork, user_id: int, item: RewardItem) -> RewardBundle:
        coins = -item.price_coins
        if item.kind is ItemKind.VIP_DAYS:
            return RewardBundle(coins=coins, vip_days=item.vip_days or 0)
        if item.kind is ItemKind.VIP_TICKET:
            return RewardBundle(coins=coins, tickets=item.ticket_count or 0)
        frame = await uow.wallets.get_frame(item.frame_id) if item.frame_id is not None else None
        if frame is None or not frame.is_active:
            raise RewardItemUnavailableError()
        owned = await uow.wallets.get_user_frame(user_id, frame.id)
        if owned is not None and owned.is_permanent:
            raise FrameAlreadyOwnedError()
        return RewardBundle(coins=coins, frame=FrameGrant(frame.code, FrameSource.REDEMPTION))
