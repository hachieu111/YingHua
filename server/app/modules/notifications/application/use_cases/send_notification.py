from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.notifications.application.delivery import deliver_notification
from app.modules.notifications.application.dto import NotificationOutcome, NotificationRequest
from app.modules.notifications.application.ports import EmailSender, NotificationsUnitOfWork


class SendNotificationUseCase:
    """F14.05 — Gửi thông báo tới một người dùng (chức năng nội bộ; hỗ trợ US-QT-11, US-QT-12, US-HG-04).

    Luôn tạo thông báo trong ứng dụng; có `email_to` thì gửi thêm email và ghi trạng thái gửi. Email lỗi: ghi
    log, trả `email_failed`, thông báo trong ứng dụng vẫn được giữ. Nội dung hiển thị như văn bản thuần.
    """

    def __init__(
        self, uow_factory: Callable[[], NotificationsUnitOfWork], email: EmailSender, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._email = email
        self._clock = clock

    async def execute(self, request: NotificationRequest) -> NotificationOutcome:
        async with self._uow_factory() as uow:
            outcome = await deliver_notification(uow, self._email, request, self._clock.now())
            await uow.commit()
        return outcome
