"""Nạp thẻ có kiểm quyền cho các use case của M08."""

from __future__ import annotations

from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.domain.entities import Card
from app.modules.review.domain.errors import CardNotFoundError


async def load_card_for_update(uow: ReviewUnitOfWork, owner_id: int, card_id: int) -> Card:
    """Khóa dòng thẻ của chủ sở hữu; thẻ của người khác được trả lời như không tồn tại."""
    card = await uow.cards.get_for_update(owner_id, card_id)
    if card is None:
        raise CardNotFoundError()
    return card
