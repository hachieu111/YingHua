from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.modules.review.application.ports import CardRepository, RetrievabilityEstimator

NEW_CARD_RETRIEVABILITY = 0.0


class EstimateRetrievabilityUseCase:
    """F09.01 (hỗ trợ US-NH-45) — Khả năng nhớ R hiện tại của từng mục từ, để M09 chọn từ ra đề.

    R của một từ là R nhỏ nhất trong các thẻ không tạm ngưng (mặt yếu nhất quyết định từ có sắp quên không);
    nếu mọi thẻ đều tạm ngưng thì xét tất cả thẻ. Thẻ mới chưa ôn có R = 0, mục từ chưa có thẻ cũng coi R = 0.
    Chức năng nội bộ chỉ đọc: M09 truyền repository thẻ gắn với phiên của giao dịch đang mở.
    """

    def __init__(self, estimator: RetrievabilityEstimator) -> None:
        self._estimator = estimator

    async def execute(
        self, cards: CardRepository, user_id: int, vocab_entry_ids: Sequence[int], now: datetime
    ) -> dict[int, float]:
        by_entry: dict[int, list[float]] = {}
        suspended_only: dict[int, list[float]] = {}
        for card in await cards.list_for_entries(user_id, vocab_entry_ids):
            r = self._estimator.retrievability(card.schedule, now)
            target = suspended_only if card.is_suspended else by_entry
            target.setdefault(card.vocab_entry_id, []).append(r)
        result: dict[int, float] = {}
        for entry_id in vocab_entry_ids:
            values = by_entry.get(entry_id) or suspended_only.get(entry_id)
            result[entry_id] = min(values) if values else NEW_CARD_RETRIEVABILITY
        return result
