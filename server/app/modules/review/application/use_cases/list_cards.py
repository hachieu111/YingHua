from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import InvalidInputError
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import CardListItem, CardListPage, ListCardsQuery
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.domain.entities import CardFilter, CardState


class InvalidCardStateError(InvalidInputError):
    code = "INVALID_CARD_STATE"
    default_message = "Trạng thái thẻ phải là learning, review hoặc relearning"


class ListCardsUseCase:
    """F13.07 (US-QT-14) — Danh sách thẻ của một người học kèm từ, lọc theo trạng thái, tạm ngưng, đến hạn.

    Dành cho quản trị viên xem thẻ của người khác (qua `owner_id`); chủ sở hữu cũng gọi được cho chính mình.
    """

    def __init__(self, uow_factory: Callable[[], ReviewUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(
        self, identity: Identity, query: ListCardsQuery, owner_id: int | None = None
    ) -> CardListPage:
        owner = resolve_owner(identity, owner_id)
        try:
            state = CardState(query.state) if query.state else None
        except ValueError as exc:
            raise InvalidCardStateError() from exc
        flt = CardFilter(owner, self._clock.now(), state, query.suspended, query.due)
        async with self._uow_factory() as uow:
            cards, total = await uow.cards.search(flt, (query.page - 1) * query.size, query.size)
            faces = await uow.vocab.faces(owner, [c.vocab_entry_id for c in cards])
        return CardListPage([CardListItem(c, faces.get(c.vocab_entry_id)) for c in cards], total)
