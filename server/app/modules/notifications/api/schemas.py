from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.notifications.application.dto import NotificationPage, ReportPage, ReportView
from app.modules.notifications.domain.entities import Notification


class CreateErrorReportRequest(BaseModel):
    page_id: int = Field(gt=0, description="Trang chứa bong bóng bị lỗi")
    bubble_id: int | None = Field(
        default=None, gt=0, description="Bong bóng bị lỗi (nếu báo riêng một bong bóng)"
    )
    report_type: Literal["ocr", "translation", "other"] | None = Field(
        default=None, description="ocr: nhận diện sai · translation: dịch sai · other: khác"
    )
    description: str | None = Field(default=None, max_length=1000, description="Mô tả vấn đề")


class ResolveErrorReportRequest(BaseModel):
    status: Literal["resolved", "rejected"] = Field(description="resolved: Đã xử lý · rejected: Từ chối")
    note: str | None = Field(default=None, max_length=1000, description="Ghi chú xử lý, người báo sẽ thấy")


class ReporterResponse(BaseModel):
    id: int
    display_name: str
    email: str


class ErrorReportResponse(BaseModel):
    id: int
    status: Literal["new", "resolved", "rejected"]
    report_type: Literal["ocr", "translation", "other"]
    description: str
    resolution_note: str | None
    page_id: int | None
    bubble_id: int | None
    series_title: str | None
    chapter_number: float | None
    page_no: int | None
    bubble_text_zh: str | None
    bubble_text_vi: str | None
    reporter: ReporterResponse | None = Field(description="Chỉ có ở danh sách của quản trị viên")
    created_at: datetime
    handled_at: datetime | None

    @classmethod
    def from_view(cls, v: ReportView) -> ErrorReportResponse:
        r = v.report
        return cls(
            id=r.id,
            status=r.status.value,
            report_type=r.report_type.value,
            description=r.description,
            resolution_note=r.resolution_note,
            page_id=r.page_id,
            bubble_id=r.bubble_id,
            series_title=v.series_title,
            chapter_number=float(v.chapter_number) if v.chapter_number is not None else None,
            page_no=v.page_no,
            bubble_text_zh=v.bubble_text_zh,
            bubble_text_vi=v.bubble_text_vi,
            reporter=ReporterResponse(
                id=v.reporter.id, display_name=v.reporter.display_name, email=v.reporter.email
            )
            if v.reporter
            else None,
            created_at=r.created_at,
            handled_at=r.handled_at,
        )


class ErrorReportPageResponse(BaseModel):
    items: list[ErrorReportResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, result: ReportPage, page: int, size: int) -> ErrorReportPageResponse:
        return cls(
            items=[ErrorReportResponse.from_view(v) for v in result.items],
            total=result.total,
            page=page,
            size=size,
        )


class NotificationResponse(BaseModel):
    id: int
    kind: str
    title: str
    body: str | None = Field(description="Văn bản thuần; không dựng HTML từ trường này")
    data: dict[str, Any]
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    @classmethod
    def from_entity(cls, n: Notification) -> NotificationResponse:
        return cls(
            id=n.id,
            kind=n.kind.value,
            title=n.title,
            body=n.body,
            data=n.data,
            is_read=n.read_at is not None,
            created_at=n.created_at,
            read_at=n.read_at,
        )


class NotificationPageResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    size: int
    unread: int = Field(description="Tổng số thông báo chưa đọc của người dùng")

    @classmethod
    def from_page(cls, result: NotificationPage, page: int, size: int) -> NotificationPageResponse:
        return cls(
            items=[NotificationResponse.from_entity(n) for n in result.items],
            total=result.total,
            page=page,
            size=size,
            unread=result.unread,
        )


class UnreadCountResponse(BaseModel):
    unread: int


class MarkAllReadResponse(BaseModel):
    updated: int
    unread: int
