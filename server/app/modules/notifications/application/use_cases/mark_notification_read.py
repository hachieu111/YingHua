from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.domain.errors import NotificationNotFoundError


class MarkNotificationReadUseCase:
    """F14.06 — Đánh dấu một thông báo đã đọc. Thông báo của người khác hoặc không có → 404."""

    def __init__(self, uow_factory: Callable[[], NotificationsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, notification_id: int) -> int:
        """Trả số thông báo chưa đọc còn lại."""
        async with self._uow_factory() as uow:
            if not await uow.notifications.mark_read(identity.user_id, notification_id, self._clock.now()):
                raise NotificationNotFoundError()
            await uow.commit()
            return await uow.notifications.count_unread(identity.user_id)
