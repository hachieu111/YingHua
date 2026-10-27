from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.modules.admin.domain.moderation import ModerationFlag
from app.modules.admin.domain.system_settings import SystemSettingsSnapshot
from app.modules.auth.application.public import User


@dataclass(frozen=True, slots=True)
class UserActivity:
    """Số liệu học tập và nội dung của một người dùng, do các module sở hữu dữ liệu cung cấp."""

    status_counts: dict[str, int]  # số mục từ theo trạng thái: learning, known, ignored
    total_cards: int
    due_now: int
    reviewed_today: int
    reviews_total: int
    private_series: int
    quick_uploads: int


@dataclass(frozen=True, slots=True)
class UserOverview:
    user: User
    activity: UserActivity


@dataclass(frozen=True, slots=True)
class SystemSettingsView:
    values: SystemSettingsSnapshot
    overridden: list[str]  # khóa đã được quản trị viên đặt trong CSDL (còn lại dùng mặc định)


@dataclass(frozen=True, slots=True)
class SystemStatus:
    """Trạng thái công khai để giao diện hiện thông báo bảo trì / ẩn tính năng đang tắt."""

    maintenance_mode: bool
    llm_enabled: bool
    tts_enabled: bool
    sample_page_available: bool


@dataclass(frozen=True, slots=True)
class SamplePageCandidate:
    """Trang đủ điều kiện làm trang mẫu (F04.16), để quản trị viên chọn thay vì gõ mã trang."""

    page_id: int
    series_title: str
    chapter_number: int
    chapter_title: str | None
    page_no: int
    bubble_count: int  # số bong bóng có chữ, để chọn trang đủ nội dung cho Hover & Dịch


@dataclass(frozen=True, slots=True)
class PersonRef:
    id: int
    display_name: str
    email: str


@dataclass(frozen=True, slots=True)
class UploadItem:
    """Một ảnh gốc tải lên trong hàng chờ kiểm duyệt (F13.04)."""

    file_id: int
    page_id: int | None
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    uploaded_at: datetime
    uploader: PersonRef | None
    flags: list[ModerationFlag]
    quick_upload: bool  # trang ảnh tải nhanh (không thuộc chương nào)


@dataclass(frozen=True, slots=True)
class RemovalItem:
    id: int
    file_id: int | None
    page_id: int | None
    reason: str
    removed_at: datetime
    removed_by: PersonRef | None
    owner: PersonRef | None


@dataclass(frozen=True, slots=True)
class ModerationTarget:
    """Những gì sẽ bị đánh dấu "đã gỡ" khi gỡ một ảnh/trang."""

    root_file_id: int
    page_id: int | None
    owner_id: int | None
    file_ids: list[int]  # ảnh gốc + ảnh dẫn xuất + ảnh ngữ cảnh cắt từ ảnh đó


@dataclass(frozen=True, slots=True)
class AuditLogItem:
    id: int
    admin: PersonRef | None
    action: str
    target_type: str
    target_id: int | None
    details: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuditLogFilter:
    admin_id: int | None = None
    action: str | None = None
    target_type: str | None = None
    since: datetime | None = None
    until: datetime | None = None
