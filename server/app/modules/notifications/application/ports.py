"""Giao diện (port) của M14 Phản hồi & Thông báo."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from app.modules.admin.application.public import AuditLogRepository
from app.modules.auth.application.public import UserRepository
from app.modules.imaging.application.public import BubbleRepository
from app.modules.notifications.domain.entities import (
    ErrorReport,
    NewErrorReport,
    NewNotification,
    Notification,
    ReportStatus,
    ReportType,
)
from app.modules.settings.application.public import ReminderSetting


class ErrorReportRepository(Protocol):
    async def add(self, new_report: NewErrorReport) -> ErrorReport:
        """Raise DuplicateReportError nếu đã có báo lỗi "Mới" cùng người, trang, bong bóng và loại lỗi."""
        ...

    async def find_open(
        self, reporter_id: int, page_id: int | None, bubble_id: int | None, report_type: ReportType
    ) -> ErrorReport | None: ...

    async def get_for_update(self, report_id: int) -> ErrorReport | None: ...

    async def save(self, report: ErrorReport) -> None: ...

    async def list_for_reporter(
        self, reporter_id: int, offset: int, limit: int
    ) -> tuple[list[ErrorReport], int]:
        """Mới nhất trước, kèm tổng số."""
        ...

    async def search(
        self, status: ReportStatus | None, reporter_id: int | None, offset: int, limit: int
    ) -> tuple[list[ErrorReport], int]:
        """Báo lỗi "Mới" lên đầu rồi mới nhất trước; lọc theo trạng thái và/hoặc người báo."""
        ...


class NotificationRepository(Protocol):
    async def add(self, new_notification: NewNotification) -> Notification: ...

    async def set_delivery(self, notification_id: int, status: str, sent_at: datetime | None) -> None: ...

    async def list_in_app(
        self, user_id: int, unread_only: bool, offset: int, limit: int
    ) -> tuple[list[Notification], int]:
        """Thông báo trong ứng dụng của người dùng, mới nhất trước, kèm tổng số khớp."""
        ...

    async def count_unread(self, user_id: int) -> int: ...

    async def mark_read(self, user_id: int, notification_id: int, now: datetime) -> bool:
        """True nếu thông báo thuộc người dùng (đã đọc rồi vẫn True); False nếu không có/của người khác."""
        ...

    async def mark_all_read(self, user_id: int, now: datetime) -> int:
        """Trả số thông báo vừa được đánh dấu đã đọc."""
        ...


class ReminderLogRepository(Protocol):
    async def claim(self, user_id: int, day: date, now: datetime) -> bool:
        """Nguyên tử: ghi nhật ký nhắc của ngày; False nếu ngày đó đã có (đã gửi hoặc đã thử) — F14.04."""
        ...


class ReminderSettingsSource(Protocol):
    """Người học đã bật nhắc ôn (M02 hiện thực)."""

    async def list_enabled(self, after_user_id: int, limit: int) -> list[ReminderSetting]: ...


class DueCardCounter(Protocol):
    """Số thẻ đến hạn theo điều kiện của F08.01 (M08 hiện thực)."""

    async def count_due(self, user_id: int, now: datetime) -> int: ...


class EmailSender(Protocol):
    async def send(self, to_email: str, subject: str, body: str) -> None:
        """Raise EmailDeliveryError khi gửi thất bại."""
        ...


class NotificationsUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def reports(self) -> ErrorReportRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...

    @property
    def reminders(self) -> ReminderLogRepository: ...

    @property
    def reminder_settings(self) -> ReminderSettingsSource: ...

    @property
    def bubbles(self) -> BubbleRepository: ...

    @property
    def users(self) -> UserRepository: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    async def __aenter__(self) -> NotificationsUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
