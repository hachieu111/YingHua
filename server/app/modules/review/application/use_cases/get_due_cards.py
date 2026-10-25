from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import DueBatch
from app.modules.review.application.due import build_due_batch
from app.modules.review.application.ports import ReviewUnitOfWork
from app.modules.review.domain.rules import parse_deck


class GetDueCardsUseCase:
    """F08.01, F08.03, F08.04 — Danh sách thẻ đến hạn của phiên ôn (US-NH-38, US-NH-40, US-NH-41).

    Điều kiện `due_at <= now` được tính ngay khi truy vấn nên không cần tác vụ định kỳ (US-HG-02). Loại thẻ
    tạm ngưng và thẻ của từ "Đã thuộc"/"Bỏ qua"; thẻ quá hạn lâu nhất đứng đầu; trả tổng số và một đợt.
    """

    def __init__(self, uow_factory: Callable[[], ReviewUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, size: int, deck: str | None) -> DueBatch:
        deck_ref = parse_deck(deck)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            return await build_due_batch(uow, identity.user_id, now, size, deck_ref)
