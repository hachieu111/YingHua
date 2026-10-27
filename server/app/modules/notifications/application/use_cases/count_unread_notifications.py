from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.notifications.application.ports import NotificationsUnitOfWork


class CountUnreadNotificationsUseCase:
    """F14.06 — Số thông báo chưa đọc (truy vấn nhẹ để giao diện hỏi lại khi quay lại tab)."""

    def __init__(self, uow_factory: Callable[[], NotificationsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity) -> int:
        async with self._uow_factory() as uow:
            return await uow.notifications.count_unread(identity.user_id)
