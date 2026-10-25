from __future__ import annotations

from datetime import datetime

from app.modules.review.application.ports import CardRepository, CardScheduler
from app.modules.review.domain.entities import Card
from app.modules.review.domain.rules import new_cards


class CreateCardsForEntryUseCase:
    """F08.09 — Tạo ba thẻ (nhận diện, nhớ lại, nghe) cho mục từ vừa được tạo (hỗ trợ US-NH-31, US-NH-40).

    Chức năng nội bộ: M07 gọi trong cùng giao dịch lưu từ bằng cách truyền repository thẻ gắn với phiên
    (session) của giao dịch đó; use case này không tự commit. Lỗi ở đây làm hủy cả giao dịch lưu từ.
    """

    def __init__(self, scheduler: CardScheduler) -> None:
        self._scheduler = scheduler

    async def execute(
        self, cards: CardRepository, user_id: int, vocab_entry_id: int, now: datetime
    ) -> list[Card]:
        initial = self._scheduler.new_state(now)
        return await cards.add_many(new_cards(user_id, vocab_entry_id, initial, now))
