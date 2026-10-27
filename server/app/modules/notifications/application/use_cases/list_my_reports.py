from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.notifications.application.dto import ReportPage
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.application.views import build_report_views


class ListMyReportsUseCase:
    """F14.01 — "Báo lỗi của tôi": danh sách báo lỗi của chính người dùng kèm trạng thái và ghi chú xử lý
    (US-NH-58 TC4). Mới nhất trước, phân trang."""

    def __init__(self, uow_factory: Callable[[], NotificationsUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(self, identity: Identity, page: int, size: int) -> ReportPage:
        async with self._uow_factory() as uow:
            reports, total = await uow.reports.list_for_reporter(identity.user_id, (page - 1) * size, size)
            views = await build_report_views(uow, self._pages, identity, reports, with_reporter=False)
        return ReportPage(views, total)
