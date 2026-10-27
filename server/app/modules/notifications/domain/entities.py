"""Thực thể của M14 Phản hồi & Thông báo — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any


class ReportType(str, Enum):
    OCR = "ocr"  # nhận diện chữ sai
    TRANSLATION = "translation"  # dịch sai
    OTHER = "other"


class ReportStatus(str, Enum):
    NEW = "new"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class NotificationKind(str, Enum):
    REMINDER = "reminder"
    REPORT_RESOLVED = "report_resolved"
    REPORT_REJECTED = "report_rejected"
    CONTENT_REMOVED = "content_removed"  # ảnh/trang bị quản trị gỡ (F13.04)


class Channel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass(slots=True)
class ErrorReport:
    id: int
    reporter_id: int
    page_id: int | None
    bubble_id: int | None
    report_type: ReportType
    description: str
    status: ReportStatus
    created_at: datetime
    resolution_note: str | None = None
    handled_by: int | None = None
    handled_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewErrorReport:
    reporter_id: int
    page_id: int | None
    bubble_id: int | None
    report_type: ReportType
    description: str
    created_at: datetime


@dataclass(slots=True)
class Notification:
    id: int
    user_id: int
    kind: NotificationKind
    title: str
    body: str | None
    channel: Channel
    status: DeliveryStatus
    created_at: datetime
    data: dict[str, Any] = field(default_factory=dict)
    read_at: datetime | None = None
    sent_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewNotification:
    user_id: int
    kind: NotificationKind
    title: str
    body: str | None
    channel: Channel
    status: DeliveryStatus
    created_at: datetime
    data: dict[str, Any] = field(default_factory=dict)
    sent_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReminderCandidate:
    """Người học đã bật nhắc, kèm thông tin để quyết định có tới giờ nhắc không (F14.04)."""

    user_id: int
    timezone: str
    reminder_time: time
