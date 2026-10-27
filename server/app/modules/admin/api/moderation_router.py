from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from app.container import Container, get_container
from app.modules.admin.api.dependencies import build_content_owner_notifier
from app.modules.admin.api.schemas import (
    AuditLogPage,
    AuditLogResponse,
    ModerationUploadPage,
    ModerationUploadResponse,
    RemovalPage,
    RemovalResponse,
    RemoveContentRequest,
)
from app.modules.admin.application.dto import AuditLogFilter
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.application.use_cases.list_audit_logs import ListAuditLogsUseCase
from app.modules.admin.application.use_cases.list_content_removals import ListContentRemovalsUseCase
from app.modules.admin.application.use_cases.list_moderation_uploads import ListModerationUploadsUseCase
from app.modules.admin.application.use_cases.remove_content import RemoveContentUseCase
from app.modules.admin.infrastructure.uow import SqlAdminUnitOfWork
from app.modules.auth.api.public import Identity, require_admin

moderation_router = APIRouter(prefix="/admin/moderation", tags=["M13 Kiểm duyệt"])
audit_router = APIRouter(prefix="/admin/audit-logs", tags=["M13 Nhật ký quản trị"])


def _uow_factory(container: Container) -> Callable[[], AdminUnitOfWork]:
    def make() -> AdminUnitOfWork:
        return SqlAdminUnitOfWork(container.session_factory)

    return make


@moderation_router.get(
    "/uploads",
    response_model=ModerationUploadPage,
    summary="Hàng chờ kiểm duyệt: ảnh mới tải lên kèm cờ nghi vấn (F13.04)",
)
async def list_uploads(
    flagged_only: bool = Query(default=False, description="Chỉ ảnh bị gắn cờ nghi vấn"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> ModerationUploadPage:
    use_case = ListModerationUploadsUseCase(_uow_factory(container), container.system_settings)
    items, total = await use_case.execute(admin, flagged_only, page, size)
    return ModerationUploadPage(
        items=[ModerationUploadResponse.from_item(i) for i in items], total=total, page=page, size=size
    )


@moderation_router.post(
    "/removals",
    response_model=RemovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gỡ ảnh/trang vi phạm kèm lý do (F13.04)",
)
async def remove_content(
    body: RemoveContentRequest,
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> RemovalResponse:
    use_case = RemoveContentUseCase(
        _uow_factory(container), container.clock, build_content_owner_notifier(container)
    )
    return RemovalResponse.from_item(await use_case.execute(admin, body.page_id, body.file_id, body.reason))


@moderation_router.get("/removals", response_model=RemovalPage, summary="Danh sách đã gỡ (F13.04)")
async def list_removals(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> RemovalPage:
    items, total = await ListContentRemovalsUseCase(_uow_factory(container)).execute(admin, page, size)
    return RemovalPage(items=[RemovalResponse.from_item(i) for i in items], total=total, page=page, size=size)


@audit_router.get("", response_model=AuditLogPage, summary="Xem và lọc nhật ký quản trị (F13.06)")
async def list_audit_logs(
    admin_id: int | None = Query(default=None, ge=1, description="Người thực hiện"),
    action: str | None = Query(default=None, max_length=48, description="Loại thao tác, vd. user.locked"),
    target_type: str | None = Query(default=None, max_length=32),
    since: datetime | None = Query(default=None, description="Từ thời điểm (ISO 8601)"),
    until: datetime | None = Query(default=None, description="Trước thời điểm (ISO 8601)"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> AuditLogPage:
    filters = AuditLogFilter(admin_id, action, target_type, since, until)
    items, total = await ListAuditLogsUseCase(_uow_factory(container)).execute(admin, filters, page, size)
    return AuditLogPage(
        items=[AuditLogResponse.from_item(i) for i in items], total=total, page=page, size=size
    )
