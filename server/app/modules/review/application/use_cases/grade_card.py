from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.core.clock import Clock
from app.core.learning_events import LearningEvent, LearningSource
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import DueBatch, GradeCommand, GradeResult
from app.modules.review.application.due import build_due_batch
from app.modules.review.application.ports import CardScheduler, ReviewUnitOfWork, UserTimezoneSource
from app.modules.review.domain.entities import Card, NewReviewLog, ReviewLog
from app.modules.review.domain.errors import CardNotFoundError, CardSuspendedError, PresentationIdTakenError
from app.modules.review.domain.rules import apply_review, local_day_bounds, parse_deck, parse_rating
from app.modules.stats.application.public import ActivityDelta, study_seconds_from_ms

NEXT_BATCH_SIZE = 1


class GradeCardUseCase:
    """F08.02 — Chấm mức nhớ (Quên/Khó/Được/Dễ) và lập lịch FSRS (US-NH-39).

    Thẻ của người khác → 404. Một `presentation_id` chỉ tính một lượt ôn: gửi lại (bấm đúp) trả kết quả của
    lượt đã ghi, không lập lịch lần hai. Cập nhật thẻ và ghi lượt ôn nằm trong một giao dịch; dòng thẻ được
    khóa để hai yêu cầu đồng thời không cùng tính lượt.
    Mỗi từ chỉ hỏi một thẻ mỗi ngày ("bury siblings" như Anki): chấm xong, các thẻ khác của cùng từ đang
    đến hạn được dời sang đầu ngày hôm sau theo múi giờ người học, giữ nguyên S, D và không ghi lượt ôn — nên
    phiên ôn không hỏi lại cùng một từ và Sổ tay hết báo "Cần ôn lại" cho từ vừa ôn (chốt 25/10/2026).
    Lập lịch dùng tham số FSRS riêng của người học nếu đã có (F08.08), cộng bộ đếm hoạt động ngày rồi ghi XP
    (F16.02, khóa là mã lượt ôn) trong cùng giao dịch (F12.01, F12.02).
    """

    def __init__(
        self,
        uow_factory: Callable[[], ReviewUnitOfWork],
        scheduler: CardScheduler,
        clock: Clock,
        timezones: UserTimezoneSource | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._scheduler = scheduler
        self._clock = clock
        self._timezones = timezones

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
            profile = await uow.fsrs_profiles.get(user_id)
            after = self._scheduler.review(before, rating, now, profile)
            apply_review(card, after, rating, now)
            await uow.cards.save(card)
            await uow.cards.bury_siblings(
                user_id, card.vocab_entry_id, card.id, now, await self._next_day(identity, now)
            )
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
            await uow.activity.record(
                user_id,
                now,
                ActivityDelta(reviews_count=1, study_seconds=study_seconds_from_ms(command.duration_ms)),
            )
            await uow.learning.record(LearningEvent(user_id, LearningSource.REVIEW, str(log.id), now))
            await uow.commit()
            await uow.learning.after_commit()
            batch = await build_due_batch(uow, user_id, now, NEXT_BATCH_SIZE, deck, card.id)
        return _result(card, log, False, batch)

    async def _next_day(self, identity: Identity, now: datetime) -> datetime:
        tz_name = await self._timezones.timezone_of(identity, identity.user_id) if self._timezones else None
        return local_day_bounds(now, tz_name)[1]


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
