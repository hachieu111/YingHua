"""Dựng đợt thẻ đến hạn (F08.01) — dùng chung cho danh sách thẻ và thẻ kế tiếp sau khi chấm."""

from __future__ import annotations

from datetime import datetime

from app.modules.review.application.dto import DueBatch, DueCard
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.domain.entities import DeckKind, DeckRef


async def build_due_batch(
    uow: ReviewUnitOfWork,
    user_id: int,
    now: datetime,
    size: int,
    deck: DeckRef,
    exclude_card_id: int | None = None,
) -> DueBatch:
    """Tổng số thẻ đến hạn trong bộ thẻ và `size` thẻ quá hạn lâu nhất, kèm nội dung hai mặt."""
    entry_ids: list[int] | None = None
    if deck.kind is not DeckKind.ALL:
        entry_ids = await uow.vocab.entry_ids_for_deck(user_id, deck)
        if not entry_ids:
            return DueBatch(0, [], deck)
    total = await uow.cards.count_due(user_id, now, entry_ids, exclude_card_id)
    cards = await uow.cards.list_due(user_id, now, size, entry_ids, exclude_card_id)
    faces = await uow.vocab.faces(user_id, [c.vocab_entry_id for c in cards])
    # Thẻ mất mục từ giữa hai truy vấn (xóa đồng thời) thì bỏ qua thay vì trả thẻ rỗng.
    items = [DueCard(c, faces[c.vocab_entry_id]) for c in cards if c.vocab_entry_id in faces]
    return DueBatch(total, items, deck)
