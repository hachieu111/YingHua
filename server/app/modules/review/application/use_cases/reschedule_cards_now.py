from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.modules.review.application.ports import CardRepository


class RescheduleCardsNowUseCase:
    """F09.04 (hỗ trợ US-NH-48) — Đưa mọi thẻ của các mục từ về ôn ngay: `due_at = now`, bỏ tạm ngưng.

    Giữ nguyên S, D, số lượt và KHÔNG ghi lượt ôn (review_log) để không làm lệch mô hình FSRS.
    Chức năng nội bộ: M09 gọi trong giao dịch nộp bài bằng repository thẻ gắn với phiên của giao dịch đó;
    use case này không tự commit. Việc đổi trạng thái "Đã thuộc" của từ do M07 lo, không thuộc M08.
    """

    async def execute(
        self, cards: CardRepository, user_id: int, vocab_entry_ids: Sequence[int], now: datetime
    ) -> int:
        return await cards.reschedule_now(user_id, vocab_entry_ids, now)
