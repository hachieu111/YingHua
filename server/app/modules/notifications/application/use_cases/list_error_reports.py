from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.notifications.application.dto import ListReportsQuery, ReportPage
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.application.views import build_report_views
from app.modules.notifications.domain.entities import ReportStatus
from app.modules.notifications.domain.errors import InvalidReportStatusError


class ListErrorReportsUseCase:
    """F14.02 — Quản trị viên xem báo lỗi kèm trang, bong bóng, mô tả và người báo, lọc theo trạng thái
    (US-QT-11 TC1). Người học → 403 (TC4)."""

    def __init__(self, uow_factory: Callable[[], NotificationsUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(self, admin: Identity, query: ListReportsQuery) -> ReportPage:
        if not admin.is_admin:
            raise PermissionDeniedError()
        status = _parse_status(query.status)
        async with self._uow_factory() as uow:
            reports, total = await uow.reports.search(
                status, query.reporter_id, (query.page - 1) * query.size, query.size
            )
            views = await build_report_views(uow, self._pages, admin, reports, with_reporter=True)
        return ReportPage(views, total)


def _parse_status(value: str | None) -> ReportStatus | None:
    if value is None or value == "":
        return None
    try:
        return ReportStatus(value)
    except ValueError as exc:
        raise InvalidReportStatusError("Trạng thái lọc phải là new, resolved hoặc rejected") from exc
