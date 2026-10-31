"""Hiện thực cổng đọc trạng thái VIP: quyền đọc truyện VIP của M03 (F17.05) và hạn mức AI (F17.04)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.vip_access import ViewerVipState
from app.modules.rewards.infrastructure.orm_models import VipUnlockModel, WalletModel


class SqlVipAccess:
    """`VipAccessPort`: dùng chung phiên của giao dịch M03 nên cùng ảnh chụp dữ liệu với việc đọc truyện."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def viewer_state(self, user_id: int, series_ids: Sequence[int], now: datetime) -> ViewerVipState:
        wallet = (
            await self._session.execute(
                select(WalletModel.vip_until, WalletModel.ticket_balance).where(
                    WalletModel.user_id == user_id
                )
            )
        ).first()
        unlocked: frozenset[int] = frozenset()
        if series_ids:
            rows = await self._session.scalars(
                select(VipUnlockModel.series_id).where(
                    VipUnlockModel.user_id == user_id, VipUnlockModel.series_id.in_(list(series_ids))
                )
            )
            unlocked = frozenset(rows)
        if wallet is None:
            return ViewerVipState(False, 0, unlocked)
        vip_until, tickets = wallet
        return ViewerVipState(vip_until is not None and vip_until > now, int(tickets), unlocked)


class SqlVipStatusReader:
    """`VipStatusReader`: mỗi lần hỏi mở một phiên ngắn (chính sách AI không nằm trong giao dịch nào)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def is_vip(self, user_id: int, now: datetime) -> bool:
        async with self._session_factory() as session:
            vip_until = await session.scalar(
                select(WalletModel.vip_until).where(WalletModel.user_id == user_id)
            )
        return vip_until is not None and vip_until > now
