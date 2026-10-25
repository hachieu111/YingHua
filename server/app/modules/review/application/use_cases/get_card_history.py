from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import HistoryPage
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.domain.errors import CardNotFoundError


class GetCardHistoryUseCase:
    """F08.06 — Lịch sử ôn của một thẻ, mới nhất trước, chia trang (US-NH-43).

    Thẻ người khác → 404; quản trị viên xem qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], ReviewUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, card_id: int, page: int, size: int, owner_id: int | None = None
    ) -> HistoryPage:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            card = await uow.cards.get(owner, card_id)
            if card is None:
                raise CardNotFoundError()
            items, total = await uow.logs.list_for_card(card.id, (page - 1) * size, size)
        return HistoryPage(card, items, total)
