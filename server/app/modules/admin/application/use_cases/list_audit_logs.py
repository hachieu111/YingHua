from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import AuditLogFilter, AuditLogItem
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.auth.application.public import Identity


class ListAuditLogsUseCase:
    """F13.06 — Xem, lọc và phân trang nhật ký thao tác quản trị (mới nhất trước).

    Chỉ đọc: nhật ký không có thao tác sửa hay xóa.
    """

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, actor: Identity, filters: AuditLogFilter, page: int, size: int
    ) -> tuple[list[AuditLogItem], int]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            return await uow.audit_logs.search(filters, (page - 1) * size, size)
