from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.review.application.access import load_card_for_update
from app.modules.review.application.ports import CardScheduler, ReviewUnitOfWork
from app.modules.review.domain.entities import Card
from app.modules.review.domain.rules import reset_card


class ResetCardUseCase:
    """F08.05 — Đặt lại thẻ (US-NH-42): S, D và lịch ôn về như thẻ mới; lịch sử ôn được giữ nguyên.

    Việc xác nhận do giao diện đảm nhiệm; máy chủ chỉ nhận lệnh đã xác nhận.
    Quản trị viên thao tác thẻ của người khác qua `owner_id`; việc đó ghi nhật ký `card.reset` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], ReviewUnitOfWork], scheduler: CardScheduler, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._scheduler = scheduler
        self._clock = clock

    async def execute(self, identity: Identity, card_id: int, owner_id: int | None = None) -> Card:
        owner = resolve_owner(identity, owner_id)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            card = await load_card_for_update(uow, owner, card_id)
            reset_card(card, self._scheduler.new_state(now), now)
            await uow.cards.save(card)
            await record_admin_action(uow.audit, identity, owner, "card.reset", "card", card.id, now)
            await uow.commit()
        return card
