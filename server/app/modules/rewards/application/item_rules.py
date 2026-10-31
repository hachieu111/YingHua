"""Quy tắc kiểm tra món đổi thưởng cần tới kho dữ liệu (dùng chung tạo và sửa món, F17.09)."""

from __future__ import annotations

from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.entities import AvatarFrame, FrameAcquireKind
from app.modules.rewards.domain.errors import InvalidRewardError


async def resolve_shop_frame(uow: RewardsUnitOfWork, frame_code: str) -> AvatarFrame:
    """Khung bán ở cửa hàng phải tồn tại, đang dùng và không phải khung thưởng mùa/khung VIP."""
    frame = await uow.wallets.get_frame_by_code(frame_code)
    if frame is None or not frame.is_active:
        raise InvalidRewardError("Khung avatar không tồn tại")
    if frame.acquire_kind is not FrameAcquireKind.SHOP:
        raise InvalidRewardError("Khung thưởng mùa hoặc khung VIP không được bán ở cửa hàng")
    return frame
