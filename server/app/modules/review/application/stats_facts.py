"""Số liệu học tập cho thống kê cá nhân (F12.01): hiện thực `LearningFactsSource` của M12.

Gom từ tổng kết ôn tập của chính M08 (đã có số từ theo trạng thái, thẻ đến hạn, lượt ôn hôm nay) và
đếm lượt ôn không chọn "Quên"; M12 không phải import nội bộ của M07/M08.
"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.application.use_cases.get_review_summary import GetReviewSummaryUseCase
from app.modules.stats.application.dto import LearningFacts


class ReviewLearningFactsSource:
    def __init__(self, summary: GetReviewSummaryUseCase, uow_factory: Callable[[], ReviewUnitOfWork]) -> None:
        self._summary = summary
        self._uow_factory = uow_factory

    async def facts(self, identity: Identity, user_id: int) -> LearningFacts:
        summary = await self._summary.execute(identity, user_id)
        counts = summary.status_counts
        async with self._uow_factory() as uow:
            reviews_total = await uow.logs.count_for_user(user_id)
            recalled = await uow.logs.count_recalled_for_user(user_id)
        return LearningFacts(
            words_total=sum(counts.values()),
            words_known=counts.get("known", 0),
            words_learning=counts.get("learning", 0),
            words_ignored=counts.get("ignored", 0),
            cards_total=summary.total_cards,
            cards_due=summary.due_now,
            reviews_total=reviews_total,
            reviews_today=summary.reviewed_today,
            reviews_recalled=recalled,
        )
