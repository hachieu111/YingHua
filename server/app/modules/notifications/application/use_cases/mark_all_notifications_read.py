from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.notifications.application.ports import NotificationsUnitOfWork


class MarkAllNotificationsReadUseCase:
    """F14.06 — Đánh dấu mọi thông báo của người dùng là đã đọc; trả số thông báo vừa đổi."""

    def __init__(self, uow_factory: Callable[[], NotificationsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> int:
        async with self._uow_factory() as uow:
            changed = await uow.notifications.mark_all_read(identity.user_id, self._clock.now())
            await uow.commit()
        return changed
