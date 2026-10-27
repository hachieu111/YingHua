from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.notifications.application.dto import CreateReportCommand, ReportView
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.application.views import build_report_views
from app.modules.notifications.domain.entities import NewErrorReport
from app.modules.notifications.domain.errors import DuplicateReportError, ReportBubbleNotFoundError
from app.modules.notifications.domain.rules import normalize_report


class CreateErrorReportUseCase:
    """F14.01 — Người học báo lỗi nhận diện/dịch của một bong bóng (US-NH-58).

    Phải đọc được trang (F03.10; trang không thấy → 404). Bong bóng, nếu có, phải thuộc bản dịch của trang.
    Cần ít nhất một loại lỗi hoặc có mô tả. Đã có báo lỗi "Mới" cùng (người, trang, bong bóng, loại) thì từ
    chối `REPORT_ALREADY_EXISTS` kèm mã báo lỗi cũ. Trạng thái khởi đầu là "Mới".
    """

    def __init__(
        self, uow_factory: Callable[[], NotificationsUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity, command: CreateReportCommand) -> ReportView:
        report_type, description = normalize_report(command.report_type, command.description)
        access = await self._pages.get_page(identity, command.page_id)
        async with self._uow_factory() as uow:
            if command.bubble_id is not None:
                bubble = await uow.bubbles.get(command.bubble_id)
                if bubble is None or bubble.translation_id != access.translation_id:
                    raise ReportBubbleNotFoundError()
            existing = await uow.reports.find_open(
                identity.user_id, command.page_id, command.bubble_id, report_type
            )
            if existing is not None:
                raise DuplicateReportError(details={"report_id": existing.id})
            report = await uow.reports.add(
                NewErrorReport(
                    reporter_id=identity.user_id,
                    page_id=command.page_id,
                    bubble_id=command.bubble_id,
                    report_type=report_type,
                    description=description,
                    created_at=self._clock.now(),
                )
            )
            await uow.commit()
            views = await build_report_views(uow, self._pages, identity, [report], with_reporter=False)
        return views[0]
