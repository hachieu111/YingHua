from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import LedgerPage
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.entities import Currency


class ListLedgerUseCase:
    """F17.02 - Lịch sử nhận/tiêu của chính người gọi, mới nhất trước, lọc theo loại (US-NH-93)."""

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, currency: Currency | None, page: int, size: int
    ) -> LedgerPage:
        async with self._uow_factory() as uow:
            items, total = await uow.wallets.list_ledger(identity.user_id, currency, (page - 1) * size, size)
        return LedgerPage(items, total)
