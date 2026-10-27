from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.notifications.application.delivery import deliver_notification
from app.modules.notifications.application.dto import NotificationRequest, ReportView
from app.modules.notifications.application.ports import EmailSender, NotificationsUnitOfWork
from app.modules.notifications.application.views import build_report_views
from app.modules.notifications.domain.entities import NotificationKind, ReportStatus
from app.modules.notifications.domain.errors import ReportAlreadyHandledError, ReportNotFoundError
from app.modules.notifications.domain.rules import parse_resolution

_TITLES = {
    ReportStatus.RESOLVED: ("Báo lỗi của bạn đã được xử lý", NotificationKind.REPORT_RESOLVED),
    ReportStatus.REJECTED: ("Báo lỗi của bạn đã bị từ chối", NotificationKind.REPORT_REJECTED),
}


class ResolveErrorReportUseCase:
    """F14.02, F14.05 — Quản trị viên chuyển báo lỗi "Mới" sang "Đã xử lý" hoặc "Từ chối" kèm ghi chú
    (US-QT-11 TC2).

    Trong MỘT giao dịch: khóa dòng báo lỗi, cập nhật trạng thái/ghi chú/người xử lý, ghi nhật ký quản trị
    (F13.06) và tạo thông báo trong ứng dụng cho người báo (F14.05). Báo lỗi đã xử lý rồi → 409.
    Việc "Chạy lại" trang xử lý sai dùng endpoint chạy lại của M04 (F04.06) với `page_id` của báo lỗi.
    """

    def __init__(
        self,
        uow_factory: Callable[[], NotificationsUnitOfWork],
        pages: PageAccessPort,
        email: EmailSender,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._email = email
        self._clock = clock

    async def execute(self, admin: Identity, report_id: int, status: str, note: str | None) -> ReportView:
        if not admin.is_admin:
            raise PermissionDeniedError()
        new_status, cleaned_note = parse_resolution(status, note)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            report = await uow.reports.get_for_update(report_id)
            if report is None:
                raise ReportNotFoundError()
            if report.status is not ReportStatus.NEW:
                raise ReportAlreadyHandledError()
            report.status, report.resolution_note = new_status, cleaned_note
            report.handled_by, report.handled_at = admin.user_id, now
            await uow.reports.save(report)
            await uow.audit.add(
                admin.user_id,
                f"error_report.{new_status.value}",
                "error_report",
                report.id,
                {"reporter_id": report.reporter_id, "page_id": report.page_id},
                now,
            )
            title, kind = _TITLES[new_status]
            await deliver_notification(
                uow,
                self._email,
                NotificationRequest(
                    user_id=report.reporter_id,
                    kind=kind,
                    title=title,
                    body=cleaned_note,
                    data={"report_id": report.id, "page_id": report.page_id, "status": new_status.value},
                ),
                now,
            )
            await uow.commit()
            views = await build_report_views(uow, self._pages, admin, [report], with_reporter=True)
        return views[0]
