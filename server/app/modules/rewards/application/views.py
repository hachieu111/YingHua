"""Dựng view ví/VIP/khung dùng chung cho các use case của M17 (đọc, không ghi)."""

from __future__ import annotations

from datetime import datetime

from app.modules.rewards.application.dto import VipStatus, WalletView
from app.modules.rewards.application.ports import WalletRepository
from app.modules.rewards.domain.entities import AvatarFrame, FrameAcquireKind, Wallet
from app.modules.rewards.domain.rules import vip_days_left


def vip_status_of(wallet: Wallet | None, now: datetime) -> VipStatus:
    if wallet is None:
        return VipStatus(False, None, 0)
    return VipStatus(wallet.is_vip(now), wallet.vip_until, vip_days_left(wallet.vip_until, now))


async def effective_equipped_frame(
    wallets: WalletRepository, wallet: Wallet, now: datetime
) -> AvatarFrame | None:
    """Khung đang đeo, chỉ khi còn hiệu lực lúc này (khung tạm hết hạn, khung VIP khi hết VIP tự ẩn)."""
    if wallet.equipped_frame_id is None:
        return None
    frame = await wallets.get_frame(wallet.equipped_frame_id)
    if frame is None or not frame.is_active:
        return None
    if frame.acquire_kind is FrameAcquireKind.VIP:
        return frame if wallet.is_vip(now) else None
    owned = await wallets.get_user_frame(wallet.user_id, frame.id)
    return frame if owned is not None and owned.is_valid(now) else None


async def build_wallet_view(wallets: WalletRepository, user_id: int, now: datetime) -> WalletView:
    """Ví chưa tạo thì mọi số bằng 0, không tạo dòng (F17.02)."""
    wallet = await wallets.get_wallet(user_id)
    if wallet is None:
        return WalletView(0, 0, vip_status_of(None, now), None)
    return WalletView(
        wallet.coin_balance,
        wallet.ticket_balance,
        vip_status_of(wallet, now),
        await effective_equipped_frame(wallets, wallet, now),
    )
