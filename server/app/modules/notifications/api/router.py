from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.auth.api.public import Identity, get_identity
from app.modules.notifications.api.dependencies import NotificationServices, get_notification_services
from app.modules.notifications.api.schemas import (
    CreateErrorReportRequest,
    ErrorReportPageResponse,
    ErrorReportResponse,
    MarkAllReadResponse,
    NotificationPageResponse,
    UnreadCountResponse,
)
from app.modules.notifications.application.dto import CreateReportCommand, ListNotificationsQuery

router = APIRouter(tags=["M14 Thông báo"])


@router.post(
    "/error-reports",
    response_model=ErrorReportResponse,
    status_code=201,
    summary="Báo lỗi nhận diện/dịch của một bong bóng (F14.01)",
)
async def create_error_report(
    body: CreateErrorReportRequest,
    identity: Identity = Depends(get_identity),
    services: NotificationServices = Depends(get_notification_services),
) -> ErrorReportResponse:
    command = CreateReportCommand(body.page_id, body.bubble_id, body.report_type, body.description)
    return ErrorReportResponse.from_view(await services.create_report.execute(identity, command))


@router.get(
    "/error-reports",
    response_model=ErrorReportPageResponse,
    summary="Báo lỗi của tôi, kèm trạng thái và ghi chú xử lý (F14.01)",
)
async def list_my_error_reports(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: NotificationServices = Depends(get_notification_services),
) -> ErrorReportPageResponse:
    result = await services.my_reports.execute(identity, page, size)
    return ErrorReportPageResponse.from_page(result, page, size)


@router.get(
    "/notifications",
    response_model=NotificationPageResponse,
    summary="Danh sách thông báo của tôi (F14.06)",
)
async def list_notifications(
    unread_only: bool = Query(default=False, description="true: chỉ thông báo chưa đọc"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: NotificationServices = Depends(get_notification_services),
) -> NotificationPageResponse:
    result = await services.list_notifications.execute(
        identity, ListNotificationsQuery(unread_only, page, size)
    )
    return NotificationPageResponse.from_page(result, page, size)


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
    summary="Số thông báo chưa đọc (truy vấn nhẹ cho chuông thông báo) (F14.06)",
)
async def unread_count(
    identity: Identity = Depends(get_identity),
    services: NotificationServices = Depends(get_notification_services),
) -> UnreadCountResponse:
    return UnreadCountResponse(unread=await services.count_unread.execute(identity))


@router.post(
    "/notifications/read-all",
    response_model=MarkAllReadResponse,
    summary="Đánh dấu mọi thông báo là đã đọc (F14.06)",
)
async def mark_all_read(
    identity: Identity = Depends(get_identity),
    services: NotificationServices = Depends(get_notification_services),
) -> MarkAllReadResponse:
    return MarkAllReadResponse(updated=await services.mark_all_read.execute(identity), unread=0)


@router.post(
    "/notifications/{notification_id}/read",
    response_model=UnreadCountResponse,
    summary="Đánh dấu một thông báo là đã đọc; trả số chưa đọc còn lại (F14.06)",
)
async def mark_read(
    notification_id: int,
    identity: Identity = Depends(get_identity),
    services: NotificationServices = Depends(get_notification_services),
) -> UnreadCountResponse:
    return UnreadCountResponse(unread=await services.mark_read.execute(identity, notification_id))
