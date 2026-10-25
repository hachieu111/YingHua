"""Số liệu học tập của một người dùng cho trang tổng quan của quản trị viên (F13.07).

Gom từ các use case đã có của M08 (tổng kết ôn tập) và M03 (đếm nội dung) qua giao diện công khai; hiện thực
`UserActivitySource` của M13 mà M13 không phải import module nào ngoài M01.
"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import UserActivity
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import CountUserContentUseCase
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.application.use_cases.get_review_summary import GetReviewSummaryUseCase


class ReviewLibraryActivitySource:
    def __init__(
        self,
        summary: GetReviewSummaryUseCase,
        content: CountUserContentUseCase,
        uow_factory: Callable[[], ReviewUnitOfWork],
    ) -> None:
        self._summary = summary
        self._content = content
        self._uow_factory = uow_factory

    async def collect(self, actor: Identity, user_id: int) -> UserActivity:
        summary = await self._summary.execute(actor, user_id)
        content = await self._content.execute(actor, user_id)
        async with self._uow_factory() as uow:
            reviews_total = await uow.logs.count_for_user(user_id)
        return UserActivity(
            status_counts=summary.status_counts,
            total_cards=summary.total_cards,
            due_now=summary.due_now,
            reviewed_today=summary.reviewed_today,
            reviews_total=reviews_total,
            private_series=content.private_series,
            quick_uploads=content.quick_uploads,
        )
