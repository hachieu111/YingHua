"""DTO của M14."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.modules.notifications.domain.entities import ErrorReport, Notification, NotificationKind


@dataclass(frozen=True, slots=True)
class CreateReportCommand:
    page_id: int
    bubble_id: int | None = None
    report_type: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ListReportsQuery:
    status: str | None = None
    reporter_id: int | None = None
    page: int = 1
    size: int = 20


@dataclass(frozen=True, slots=True)
class ReporterInfo:
    id: int
    display_name: str
    email: str


@dataclass(frozen=True, slots=True)
class ReportView:
    """Báo lỗi kèm vị trí đọc được (truyện, chương, trang) và nội dung bong bóng tại lúc xem."""

    report: ErrorReport
    series_title: str | None = None
    chapter_number: Decimal | None = None
    page_no: int | None = None
    bubble_text_zh: str | None = None
    bubble_text_vi: str | None = None
    reporter: ReporterInfo | None = None  # chỉ có ở danh sách của quản trị viên


@dataclass(frozen=True, slots=True)
class NotificationRequest:
    """F14.05 — Một thông báo gửi tới người dùng. Có `email_to` thì gửi thêm email (kênh email)."""

    user_id: int
    kind: NotificationKind
    title: str
    body: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    email_to: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationOutcome:
    in_app: Notification
    email: Notification | None = None

    @property
    def email_failed(self) -> bool:
        return self.email is not None and self.email.status.value == "failed"


@dataclass(frozen=True, slots=True)
class ListNotificationsQuery:
    unread_only: bool = False
    page: int = 1
    size: int = 20


@dataclass(frozen=True, slots=True)
class ReminderConfig:
    grace_hours: int


@dataclass(frozen=True, slots=True)
class ReminderReport:
    """Tóm tắt một lần quét nhắc ôn (F14.04), ghi vào `job_runs.summary`."""

    scanned: int = 0
    sent: int = 0
    skipped_not_due_time: int = 0
    skipped_no_cards: int = 0
    skipped_already: int = 0
    skipped_locked: int = 0
    email_failed: int = 0

    def as_summary(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "sent": self.sent,
            "skipped_not_due_time": self.skipped_not_due_time,
            "skipped_no_cards": self.skipped_no_cards,
            "skipped_already": self.skipped_already,
            "skipped_locked": self.skipped_locked,
            "email_failed": self.email_failed,
        }


@dataclass(frozen=True, slots=True)
class ReportPage:
    items: list[ReportView]
    total: int


@dataclass(frozen=True, slots=True)
class NotificationPage:
    items: list[Notification]
    total: int
    unread: int
