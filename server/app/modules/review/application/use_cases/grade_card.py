from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import DueBatch, GradeCommand, GradeResult
from app.modules.review.application.due import build_due_batch
from app.modules.review.application.ports import CardScheduler, ReviewUnitOfWork
from app.modules.review.domain.entities import Card, NewReviewLog, ReviewLog
from app.modules.review.domain.errors import CardNotFoundError, CardSuspendedError, PresentationIdTakenError
from app.modules.review.domain.rules import apply_review, parse_deck, parse_rating

NEXT_BATCH_SIZE = 1


class GradeCardUseCase:
    """F08.02 — Chấm mức nhớ (Quên/Khó/Được/Dễ) và lập lịch FSRS (US-NH-39).

    Thẻ của người khác → 404. Một `presentation_id` chỉ tính một lượt ôn: gửi lại (bấm đúp) trả kết quả của
    lượt đã ghi, không lập lịch lần hai. Cập nhật thẻ và ghi lượt ôn nằm trong một giao dịch; dòng thẻ được
    khóa để hai yêu cầu đồng thời không cùng tính lượt.
    """

    def __init__(
        self, uow_factory: Callable[[], ReviewUnitOfWork], scheduler: CardScheduler, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._scheduler = scheduler
        self._clock = clock

    async def execute(self, identity: Identity, command: GradeCommand) -> GradeResult:
        rating = parse_rating(command.rating)
        deck = parse_deck(command.deck)
        user_id = identity.user_id
        now = self._clock.now()
        async with self._uow_factory() as uow:
            card = await uow.cards.get_for_update(user_id, command.card_id)
            if card is None:
                raise CardNotFoundError()
            previous = await uow.logs.find_by_presentation(command.presentation_id)
            if previous is not None:
                if previous.card_id != card.id or previous.user_id != user_id:
                    raise PresentationIdTakenError()
                batch = await build_due_batch(uow, user_id, now, NEXT_BATCH_SIZE, deck, card.id)
                return _result(card, previous, True, batch)
            if card.is_suspended:
                raise CardSuspendedError()
            before = card.schedule
            after = self._scheduler.review(before, rating, now)
            apply_review(card, after, rating, now)
            await uow.cards.save(card)
            log = await uow.logs.add(
                NewReviewLog(
                    card_id=card.id,
                    user_id=user_id,
                    rating=rating,
                    state_before=before.state,
                    stability_before=before.stability,
                    stability_after=after.stability,
                    difficulty_before=before.difficulty,
                    difficulty_after=after.difficulty,
                    due_after=after.due_at,
                    duration_ms=command.duration_ms,
                    presentation_id=command.presentation_id,
                    reviewed_at=now,
                )
            )
            await uow.commit()
            batch = await build_due_batch(uow, user_id, now, NEXT_BATCH_SIZE, deck, card.id)
        return _result(card, log, False, batch)


def _result(card: Card, log: ReviewLog, duplicate: bool, batch: DueBatch) -> GradeResult:
    return GradeResult(
        card=card,
        rating=log.rating,
        reviewed_at=log.reviewed_at,
        due_at=log.due_after,
        interval_seconds=max(0, int((log.due_after - log.reviewed_at).total_seconds())),
        duplicate=duplicate,
        next_batch=batch,
    )
