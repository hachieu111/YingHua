from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.rewards.application.dto import GrantCommand, GrantResult
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import RewardsUnitOfWork


class GrantRewardUseCase:
    """F17.01 - Ghi sổ phần thưởng (chức năng nội bộ, cổng công khai cho M16).

    Mở giao dịch riêng, khóa ví, ghi sổ rồi lưu. Khóa chống trùng làm gọi lại không cộng hai lần
    (`GrantResult.duplicate`). Không có API nào để trình duyệt tự gọi.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, command: GrantCommand) -> GrantResult:
        async with self._uow_factory() as uow:
            result = await RewardLedger(uow.wallets).apply(command, self._clock.now())
            await uow.commit()
        return result
