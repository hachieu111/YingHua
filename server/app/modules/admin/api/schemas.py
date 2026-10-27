from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.uploads import file_url
from app.modules.admin.application.dto import (
    AuditLogItem,
    PersonRef,
    RemovalItem,
    SamplePageCandidate,
    SystemSettingsView,
    SystemStatus,
    UploadItem,
)
from app.modules.auth.application.public import User


class AdminUserResponse(BaseModel):
    """Không có mật khẩu (kể cả bản băm) hay dữ liệu học tập riêng."""

    id: int
    email: str
    display_name: str
    role: str
    status: str
    locked_reason: str | None
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_entity(cls, u: User) -> AdminUserResponse:
        return cls(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=u.role.value,
            status=u.status.value,
            locked_reason=u.locked_reason,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )


class AdminUserPage(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int


class ChangeRoleRequest(BaseModel):
    role: Literal["user", "admin"]


class LockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SystemSettingsValues(BaseModel):
    llm_enabled: bool
    tts_enabled: bool
    quiz_daily_llm_limit: int
    ai_note_daily_limit: int
    grammar_daily_limit: int
    mistake_review_daily_limit: int
    maintenance_mode: bool
    auto_moderation_enabled: bool
    ocr_on_upload_enabled: bool
    admin_notifications_enabled: bool
    sample_page_id: int | None


class SystemSettingsResponse(BaseModel):
    values: SystemSettingsValues
    overridden: list[str] = Field(description="Khóa đã được quản trị viên đặt; còn lại đang dùng mặc định")

    @classmethod
    def from_view(cls, v: SystemSettingsView) -> SystemSettingsResponse:
        return cls(values=SystemSettingsValues(**v.values.as_dict()), overridden=v.overridden)


class SamplePageCandidateResponse(BaseModel):
    page_id: int
    series_title: str
    chapter_number: int
    chapter_title: str | None
    page_no: int
    bubble_count: int = Field(description="Số bong bóng có chữ trên trang")

    @classmethod
    def from_item(cls, c: SamplePageCandidate) -> SamplePageCandidateResponse:
        return cls(
            page_id=c.page_id,
            series_title=c.series_title,
            chapter_number=c.chapter_number,
            chapter_title=c.chapter_title,
            page_no=c.page_no,
            bubble_count=c.bubble_count,
        )


class SamplePageCandidateList(BaseModel):
    items: list[SamplePageCandidateResponse]


class SystemStatusResponse(BaseModel):
    maintenance_mode: bool
    message: str | None = Field(
        description="Thông báo bảo trì hiển thị cho người dùng; null khi không bảo trì"
    )
    llm_enabled: bool
    tts_enabled: bool
    sample_page_available: bool

    @classmethod
    def from_status(cls, s: SystemStatus, maintenance_message: str) -> SystemStatusResponse:
        return cls(
            maintenance_mode=s.maintenance_mode,
            message=maintenance_message if s.maintenance_mode else None,
            llm_enabled=s.llm_enabled,
            tts_enabled=s.tts_enabled,
            sample_page_available=s.sample_page_available,
        )


class PersonResponse(BaseModel):
    id: int
    display_name: str
    email: str

    @classmethod
    def optional(cls, p: PersonRef | None) -> PersonResponse | None:
        return None if p is None else cls(id=p.id, display_name=p.display_name, email=p.email)


class ModerationUploadResponse(BaseModel):
    file_id: int
    page_id: int | None
    url: str = Field(description="Địa chỉ ảnh (kiểm quyền; quản trị viên xem được mọi ảnh chưa gỡ)")
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    uploaded_at: datetime
    uploader: PersonResponse | None
    flags: list[str] = Field(
        description="Cờ nghi vấn theo luật đơn giản; rỗng khi không có hoặc kiểm duyệt tự động tắt"
    )
    quick_upload: bool

    @classmethod
    def from_item(cls, i: UploadItem) -> ModerationUploadResponse:
        return cls(
            file_id=i.file_id,
            page_id=i.page_id,
            url=file_url(i.file_id) or "",
            mime_type=i.mime_type,
            size_bytes=i.size_bytes,
            width=i.width,
            height=i.height,
            uploaded_at=i.uploaded_at,
            uploader=PersonResponse.optional(i.uploader),
            flags=[f.value for f in i.flags],
            quick_upload=i.quick_upload,
        )


class ModerationUploadPage(BaseModel):
    items: list[ModerationUploadResponse]
    total: int
    page: int
    size: int


class RemoveContentRequest(BaseModel):
    page_id: int | None = Field(default=None, ge=1, description="Trang cần gỡ (hoặc chỉ định file_id)")
    file_id: int | None = Field(default=None, ge=1, description="Tệp ảnh cần gỡ (hoặc chỉ định page_id)")
    reason: str | None = Field(default=None, max_length=2000, description="Lý do gỡ (bắt buộc)")


class RemovalResponse(BaseModel):
    id: int
    file_id: int | None
    page_id: int | None
    reason: str
    removed_at: datetime
    removed_by: PersonResponse | None
    owner: PersonResponse | None

    @classmethod
    def from_item(cls, i: RemovalItem) -> RemovalResponse:
        return cls(
            id=i.id,
            file_id=i.file_id,
            page_id=i.page_id,
            reason=i.reason,
            removed_at=i.removed_at,
            removed_by=PersonResponse.optional(i.removed_by),
            owner=PersonResponse.optional(i.owner),
        )


class RemovalPage(BaseModel):
    items: list[RemovalResponse]
    total: int
    page: int
    size: int


class AuditLogResponse(BaseModel):
    id: int
    admin: PersonResponse | None
    action: str
    target_type: str
    target_id: int | None
    details: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_item(cls, i: AuditLogItem) -> AuditLogResponse:
        return cls(
            id=i.id,
            admin=PersonResponse.optional(i.admin),
            action=i.action,
            target_type=i.target_type,
            target_id=i.target_id,
            details=i.details,
            created_at=i.created_at,
        )


class AuditLogPage(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    size: int
