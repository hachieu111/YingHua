from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.notifications.application.dto import ListNotificationsQuery, NotificationPage
from app.modules.notifications.application.ports import NotificationsUnitOfWork


class ListNotificationsUseCase:
    """F14.06 — Danh sách thông báo trong ứng dụng của chính người dùng, mới nhất trước; lọc chưa đọc."""

    def __init__(self, uow_factory: Callable[[], NotificationsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, query: ListNotificationsQuery) -> NotificationPage:
        async with self._uow_factory() as uow:
            items, total = await uow.notifications.list_in_app(
                identity.user_id, query.unread_only, (query.page - 1) * query.size, query.size
            )
            unread = await uow.notifications.count_unread(identity.user_id)
        return NotificationPage(items, total, unread)
