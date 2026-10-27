"""Cầu nối M13 -> M14: thông báo cho người tải ảnh khi ảnh bị gỡ (F13.04 bước 4, F14.05)."""

from __future__ import annotations

from app.modules.notifications.application.public import (
    NotificationKind,
    NotificationRequest,
    SendNotificationUseCase,
)

REMOVED_TITLE = "Ảnh của bạn đã bị gỡ"


class NotificationsContentOwnerNotifier:
    """Gọi use case công khai F14.05 của M14 (thông báo trong ứng dụng, không gửi email)."""

    def __init__(self, send: SendNotificationUseCase) -> None:
        self._send = send

    async def content_removed(self, owner_id: int, page_id: int | None, reason: str) -> None:
        data = {} if page_id is None else {"page_id": page_id}
        await self._send.execute(
            NotificationRequest(
                user_id=owner_id,
                kind=NotificationKind.CONTENT_REMOVED,
                title=REMOVED_TITLE,
                body=f"Lý do: {reason}",
                data=data,
            )
        )
