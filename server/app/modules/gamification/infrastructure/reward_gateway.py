"""Cầu nối M16 -> M17: ghi phần thưởng vào sổ (F17.01) trên CÙNG phiên (giao dịch) với M16."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rewards.application.public import (
    Decoration,
    GrantCommand,
    GrantResult,
    LedgerReason,
    RewardBundle,
    RewardLedger,
)
from app.modules.rewards.infrastructure.public import SqlWalletRepository


class SessionRewardGateway:
    """Dùng `RewardLedger` của M17 với kho ví chạy trên phiên của M16: xu, vé, VIP, khung và sự kiện XP/kết
    quả mùa cùng lưu hoặc cùng hủy, không có trạng thái "đã thưởng nhưng mất XP"."""

    def __init__(self, session: AsyncSession) -> None:
        self._wallets = SqlWalletRepository(session)
        self._ledger = RewardLedger(self._wallets)

    async def grant(
        self, user_id: int, bundle: RewardBundle, key: str, reason: LedgerReason | None, now: datetime
    ) -> GrantResult:
        return await self._ledger.apply(GrantCommand(user_id, bundle, key, reason), now)

    async def decorations(self, user_ids: Sequence[int], now: datetime) -> Mapping[int, Decoration]:
        if not user_ids:
            return {}
        return await self._wallets.decorations(user_ids, now)
