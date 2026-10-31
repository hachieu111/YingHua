from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.entities import AvatarFrame, FrameAcquireKind
from app.modules.rewards.domain.errors import FrameNotAvailableError


class EquipFrameUseCase:
    """F17.08 - Đeo (hoặc tháo, khi `frame_code` là None) khung avatar (US-NH-99).

    Đeo được khi đã sở hữu và còn hạn, hoặc là khung VIP và người dùng đang VIP; ngược lại 409
    `FRAME_NOT_AVAILABLE` và khung đang đeo giữ nguyên.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, frame_code: str | None) -> AvatarFrame | None:
        now, user_id = self._clock.now(), identity.user_id
        async with self._uow_factory() as uow:
            wallet = await uow.wallets.lock_wallet(user_id, now)
            frame = None
            if frame_code is not None:
                frame = await uow.wallets.get_frame_by_code(frame_code)
                if frame is None or not frame.is_active:
                    raise FrameNotAvailableError()
                if frame.acquire_kind is FrameAcquireKind.VIP:
                    usable = wallet.is_vip(now)
                else:
                    owned = await uow.wallets.get_user_frame(user_id, frame.id)
                    usable = owned is not None and owned.is_valid(now)
                if not usable:
                    raise FrameNotAvailableError()
            wallet.equipped_frame_id = frame.id if frame else None
            await uow.wallets.save_wallet(wallet, now)
            await uow.commit()
        return frame
