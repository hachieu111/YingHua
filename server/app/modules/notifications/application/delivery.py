"""Gửi một thông báo trên giao dịch đang mở (F14.05): bản ghi trong ứng dụng + email tùy chọn."""

from __future__ import annotations

import logging
from datetime import datetime

from app.modules.notifications.application.dto import NotificationOutcome, NotificationRequest
from app.modules.notifications.application.ports import EmailSender, NotificationsUnitOfWork
from app.modules.notifications.domain.entities import Channel, DeliveryStatus, NewNotification
from app.modules.notifications.domain.errors import EmailDeliveryError
from app.modules.notifications.domain.rules import clip_title

logger = logging.getLogger(__name__)


async def deliver_notification(
    uow: NotificationsUnitOfWork, email_sender: EmailSender, request: NotificationRequest, now: datetime
) -> NotificationOutcome:
    """Tạo thông báo trong ứng dụng (luôn thành công), rồi gửi email nếu có `email_to`.

    Email lỗi chỉ đánh dấu `failed` và ghi log; thông báo trong ứng dụng vẫn được giữ. Người gọi chịu trách
    nhiệm `commit()`. Nội dung là văn bản thuần (giao diện không được dựng HTML từ đó).
    """
    title = clip_title(request.title)
    in_app = await uow.notifications.add(
        NewNotification(
            user_id=request.user_id,
            kind=request.kind,
            title=title,
            body=request.body,
            channel=Channel.IN_APP,
            status=DeliveryStatus.SENT,
            created_at=now,
            data=request.data,
            sent_at=now,
        )
    )
    if request.email_to is None:
        return NotificationOutcome(in_app)
    email = await uow.notifications.add(
        NewNotification(
            user_id=request.user_id,
            kind=request.kind,
            title=title,
            body=request.body,
            channel=Channel.EMAIL,
            status=DeliveryStatus.PENDING,
            created_at=now,
            data=request.data,
        )
    )
    try:
        await email_sender.send(request.email_to, title, request.body or "")
    except EmailDeliveryError:
        logger.warning("Gửi email thông báo %s cho người dùng %s thất bại", email.id, request.user_id)
        email.status, email.sent_at = DeliveryStatus.FAILED, None
    else:
        email.status, email.sent_at = DeliveryStatus.SENT, now
    await uow.notifications.set_delivery(email.id, email.status.value, email.sent_at)
    return NotificationOutcome(in_app, email)
