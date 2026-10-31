from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.rewards.application.dto import GrantCommand
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import RewardNotifier, RewardsUnitOfWork
from app.modules.rewards.domain.entities import LedgerReason, RewardBundle
from app.modules.rewards.domain.rules import WELCOME_KEY, WELCOME_VIP_DAYS


class GrantWelcomeGiftUseCase:
    """F17.03 - Quà chào mừng: 3 ngày VIP cho tài khoản mới, đúng một lần (US-NH-94).

    Hiện thực `WelcomeGiftPort` (core) để M01 gọi lúc đăng ký (F01.01) mà không import M17. Khóa chống trùng
    `welcome` nên gọi lại không cấp lần hai. Lỗi để bên gọi bắt: đăng ký vẫn thành công (M01 ghi cảnh báo).
    """

    def __init__(
        self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock, notifier: RewardNotifier
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._notifier = notifier

    async def grant_welcome(self, user_id: int) -> None:
        command = GrantCommand(
            user_id, RewardBundle(vip_days=WELCOME_VIP_DAYS), WELCOME_KEY, LedgerReason.WELCOME
        )
        async with self._uow_factory() as uow:
            result = await RewardLedger(uow.wallets).apply(command, self._clock.now())
            await uow.commit()
        if not result.duplicate and result.wallet.vip_until is not None:
            await self._notifier.vip_granted(user_id, WELCOME_VIP_DAYS, result.wallet.vip_until, None)
