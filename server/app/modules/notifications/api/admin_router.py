from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.auth.api.public import Identity, require_admin
from app.modules.notifications.api.dependencies import NotificationServices, get_notification_services
from app.modules.notifications.api.schemas import (
    ErrorReportPageResponse,
    ErrorReportResponse,
    ResolveErrorReportRequest,
)
from app.modules.notifications.application.dto import ListReportsQuery

admin_router = APIRouter(prefix="/admin/error-reports", tags=["M14 Thông báo"])


@admin_router.get(
    "",
    response_model=ErrorReportPageResponse,
    summary="Quản trị: danh sách báo lỗi, lọc theo trạng thái (F14.02)",
)
async def list_error_reports(
    status: str | None = Query(default=None, max_length=12, description="new | resolved | rejected"),
    reporter_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: Identity = Depends(require_admin),
    services: NotificationServices = Depends(get_notification_services),
) -> ErrorReportPageResponse:
    result = await services.list_reports.execute(admin, ListReportsQuery(status, reporter_id, page, size))
    return ErrorReportPageResponse.from_page(result, page, size)


@admin_router.patch(
    "/{report_id}",
    response_model=ErrorReportResponse,
    summary="Quản trị: đánh dấu báo lỗi Đã xử lý/Từ chối kèm ghi chú; thông báo cho người báo (F14.02)",
)
async def resolve_error_report(
    report_id: int,
    body: ResolveErrorReportRequest,
    admin: Identity = Depends(require_admin),
    services: NotificationServices = Depends(get_notification_services),
) -> ErrorReportResponse:
    view = await services.resolve_report.execute(admin, report_id, body.status, body.note)
    return ErrorReportResponse.from_view(view)
