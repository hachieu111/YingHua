from __future__ import annotations

import uuid
from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import GrantCommand, UnlockResult
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.entities import Currency, LedgerReason, RewardBundle, UnlockSource, VipUnlock
from app.modules.rewards.domain.errors import (
    RequestReusedError,
    SeriesAlreadyUnlockedError,
    SeriesNotVipError,
    VipSeriesNotFoundError,
)

UNLOCK_TICKET_COST = 1


class UnlockSeriesUseCase:
    """F17.06 - Mở khóa vĩnh viễn một truyện VIP bằng một vé (US-NH-97).

    Một giao dịch: khóa ví, kiểm tra, trừ vé qua sổ (khóa chống trùng là mã yêu cầu) và ghi bản ghi mở khóa.
    Gửi lại cùng mã yêu cầu trả lại kết quả cũ, không trừ vé lần hai. Mở khóa không phụ thuộc trạng thái VIP.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, series_id: int, request_id: uuid.UUID) -> UnlockResult:
        now, user_id, key = self._clock.now(), identity.user_id, str(request_id)
        async with self._uow_factory() as uow:
            wallet = await uow.wallets.lock_wallet(user_id, now)  # tuần tự hóa hai yêu cầu đồng thời
            if await uow.wallets.has_ledger_key(user_id, Currency.TICKET, key):
                existing = await uow.unlocks.get(user_id, series_id)
                if existing is None:
                    raise RequestReusedError()
                return UnlockResult(existing, wallet.ticket_balance)
            series = await uow.series.get(series_id)
            if series is None or (not series.is_public and series.owner_id != user_id):
                raise VipSeriesNotFoundError()
            if not series.is_vip:
                raise SeriesNotVipError()
            if await uow.unlocks.get(user_id, series_id) is not None:
                raise SeriesAlreadyUnlockedError()
            command = GrantCommand(
                user_id, RewardBundle(tickets=-UNLOCK_TICKET_COST), key, LedgerReason.VIP_UNLOCK
            )
            granted = await RewardLedger(uow.wallets).apply(command, now)
            unlock = VipUnlock(user_id, series_id, UnlockSource.TICKET, now)
            await uow.unlocks.add(unlock)
            await uow.commit()
        return UnlockResult(unlock, granted.wallet.ticket_balance)
