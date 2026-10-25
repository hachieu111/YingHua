from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.review.application.access import load_card_for_update
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.domain.entities import Card


class ResumeCardUseCase:
    """F08.05 — Tiếp tục thẻ (US-NH-42): giữ hạn ôn theo FSRS hiện tại, đã qua hạn thì đến hạn ngay.

    Quản trị viên thao tác thẻ của người khác qua `owner_id`; việc đó ghi nhật ký `card.resume` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], ReviewUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, card_id: int, owner_id: int | None = None) -> Card:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            card = await load_card_for_update(uow, owner, card_id)
            if card.is_suspended:
                card.is_suspended = False
                card.updated_at = self._clock.now()
                await uow.cards.save(card)
                await record_admin_action(
                    uow.audit, identity, owner, "card.resume", "card", card.id, card.updated_at
                )
                await uow.commit()
        return card
