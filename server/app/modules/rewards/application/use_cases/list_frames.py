from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import FrameView
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.views import effective_equipped_frame
from app.modules.rewards.domain.entities import AvatarFrame, FrameAcquireKind, UserFrame


def frame_view(
    frame: AvatarFrame, owned: UserFrame | None, is_vip: bool, equipped_id: int | None, now: datetime
) -> FrameView:
    """Khung VIP dùng được khi đang VIP (không cần sở hữu); khung khác cần sở hữu còn hạn."""
    if frame.acquire_kind is FrameAcquireKind.VIP:
        usable, expires = is_vip, None
    else:
        usable = owned is not None and owned.is_valid(now)
        expires = owned.expires_at if owned is not None else None
    return FrameView(frame, usable, expires, usable, equipped_id == frame.id and usable)


class ListFramesUseCase:
    """F17.08 - Mọi khung đang dùng kèm cách kiếm, đã sở hữu, hạn dùng, đeo được, đang đeo (US-NH-99)."""

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> list[FrameView]:
        now, user_id = self._clock.now(), identity.user_id
        async with self._uow_factory() as uow:
            frames = await uow.wallets.list_frames()
            owned = {f.frame_id: f for f in await uow.wallets.list_user_frames(user_id)}
            wallet = await uow.wallets.get_wallet(user_id)
            equipped = None
            if wallet is not None:
                effective = await effective_equipped_frame(uow.wallets, wallet, now)
                equipped = effective.id if effective else None
        is_vip = wallet is not None and wallet.is_vip(now)
        return [frame_view(f, owned.get(f.id), is_vip, equipped, now) for f in frames]
