from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import GrantCommand, WalletAdjustCommand, WalletView
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import RewardNotifier, RewardsUnitOfWork
from app.modules.rewards.application.use_cases.grant_vip import admin_key, require_reason
from app.modules.rewards.application.views import build_wallet_view
from app.modules.rewards.domain.entities import Currency, LedgerReason, RewardBundle
from app.modules.rewards.domain.errors import (
    InvalidRewardError,
    NotEnoughCoinsError,
    NotEnoughTicketsError,
    WalletNegativeError,
)


class AdjustWalletUseCase:
    """F17.10 - Quản trị viên điều chỉnh xu hoặc vé của một người dùng (US-QT-18).

    Số lượng dương hoặc âm, khác 0, trong giới hạn F17.01 (xu 100.000, vé 10 mỗi lần); kết quả không được âm
    (409 `WALLET_NEGATIVE`). Được phép tự điều chỉnh cho chính mình; ghi nhật ký `rewards.wallet_adjusted`
    trong cùng giao dịch, thông báo gửi sau khi lưu.
    """

    def __init__(
        self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock, notifier: RewardNotifier
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._notifier = notifier

    async def execute(self, actor: Identity, command: WalletAdjustCommand) -> WalletView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        reason = require_reason(command.reason)
        if command.amount == 0:
            raise InvalidRewardError("Số lượng điều chỉnh phải khác 0")
        bundle = self._bundle_of(command)
        now, target = self._clock.now(), command.user_id
        grant = GrantCommand(
            target, bundle, admin_key(command.request_id), LedgerReason.ADMIN_ADJUST, actor.user_id, reason
        )
        async with self._uow_factory() as uow:
            try:
                result = await RewardLedger(uow.wallets).apply(grant, now)
            except (NotEnoughCoinsError, NotEnoughTicketsError) as exc:
                raise WalletNegativeError(details=exc.details) from exc
            if result.duplicate:
                # Gửi lại cùng mã yêu cầu: trả ví hiện tại, không ghi nhật ký hay thông báo lần hai.
                return await build_wallet_view(uow.wallets, target, now)
            await uow.audit.add(
                actor.user_id,
                "rewards.wallet_adjusted",
                "user",
                target,
                {
                    "target_user_id": target,
                    "currency": command.currency.value,
                    "amount": command.amount,
                    "reason": reason,
                },
                now,
            )
            view = await build_wallet_view(uow.wallets, target, now)
            await uow.commit()
        await self._notifier.wallet_adjusted(target, command.currency, command.amount, reason)
        return view

    @staticmethod
    def _bundle_of(command: WalletAdjustCommand) -> RewardBundle:
        if command.currency is Currency.COIN:
            return RewardBundle(coins=command.amount)
        if command.currency is Currency.TICKET:
            return RewardBundle(tickets=command.amount)
        raise InvalidRewardError("Chỉ điều chỉnh được xu hoặc vé; dùng cấp/thu VIP cho ngày VIP")
