"""Dựng `ReportView` (vị trí đọc được + nội dung bong bóng) cho danh sách báo lỗi."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.notifications.application.dto import ReporterInfo, ReportView
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.domain.entities import ErrorReport


async def build_report_views(
    uow: NotificationsUnitOfWork,
    pages: PageAccessPort,
    identity: Identity,
    reports: Sequence[ErrorReport],
    *,
    with_reporter: bool,
) -> list[ReportView]:
    """Gom thông tin trang, bong bóng và người báo theo lô (không N+1 trên bong bóng và người dùng)."""
    page_ids = list(dict.fromkeys(r.page_id for r in reports if r.page_id is not None))
    accesses = {a.page_id: a for a in await pages.describe_pages(identity, page_ids)} if page_ids else {}
    bubble_ids = [r.bubble_id for r in reports if r.bubble_id is not None]
    bubbles = await uow.bubbles.get_many(bubble_ids) if bubble_ids else {}
    users = await uow.users.get_many([r.reporter_id for r in reports]) if with_reporter else {}
    views: list[ReportView] = []
    for report in reports:
        page = accesses.get(report.page_id) if report.page_id is not None else None
        bubble = bubbles.get(report.bubble_id) if report.bubble_id is not None else None
        user = users.get(report.reporter_id)
        views.append(
            ReportView(
                report=report,
                series_title=page.series_title if page else None,
                chapter_number=page.chapter_number if page else None,
                page_no=page.page_no if page else None,
                bubble_text_zh=bubble.text_zh if bubble else None,
                bubble_text_vi=bubble.text_vi if bubble else None,
                reporter=ReporterInfo(user.id, user.display_name, user.email) if user else None,
            )
        )
    return views
