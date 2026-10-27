from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    ColumnElement,
    String,
    and_,
    case,
    column,
    func,
    not_,
    select,
    table,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.review.domain.entities import (
    Card,
    CardFilter,
    CardState,
    CardType,
    EntrySrsSummary,
    NewCard,
    NewReviewLog,
    Rating,
    ReviewLog,
    SchedulingState,
)
from app.modules.review.domain.errors import PresentationIdTakenError
from app.modules.review.domain.fsrs_profile import OptimizerLog
from app.modules.review.infrastructure.orm_models import CardModel, ReviewLogModel

# Tham chiếu chỉ-đọc tới bảng của M07 (hợp đồng lược đồ): thẻ chỉ đến hạn khi từ còn ở trạng thái "Đang học".
# Dùng bảng nhẹ thay vì import ORM của M07 để M08 không phụ thuộc vào nội bộ của M07.
_VOCAB = table(
    "vocab_entries",
    column("id", BigInteger),
    column("user_id", BigInteger),
    column("status", String),
)
_STATUS_LEARNING = "learning"


def _card(m: CardModel) -> Card:
    return Card(
        id=m.id,
        user_id=m.user_id,
        vocab_entry_id=m.vocab_entry_id,
        card_type=CardType(m.card_type),
        schedule=SchedulingState(
            state=CardState(m.state),
            step=m.step,
            stability=m.stability,
            difficulty=m.difficulty,
            due_at=m.due_at,
            last_review_at=m.last_review_at,
        ),
        reps=m.reps,
        lapses=m.lapses,
        is_suspended=m.is_suspended,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _log(m: ReviewLogModel) -> ReviewLog:
    return ReviewLog(
        id=m.id,
        card_id=m.card_id,
        user_id=m.user_id,
        rating=Rating(m.rating),
        state_before=CardState(m.state_before),
        stability_before=m.stability_before,
        stability_after=m.stability_after,
        difficulty_before=m.difficulty_before,
        difficulty_after=m.difficulty_after,
        due_after=m.due_after,
        duration_ms=m.duration_ms,
        presentation_id=m.presentation_id,
        reviewed_at=m.reviewed_at,
    )


def _eligible(user_id: int) -> list[ColumnElement[bool]]:
    """Thẻ có thể ôn: không tạm ngưng và thuộc từ "Đang học" (F08.01)."""
    learning_ids = select(_VOCAB.c.id).where(_VOCAB.c.user_id == user_id, _VOCAB.c.status == _STATUS_LEARNING)
    return [
        CardModel.user_id == user_id,
        CardModel.is_suspended.is_(False),
        CardModel.vocab_entry_id.in_(learning_ids),
    ]


def _due_conditions(
    user_id: int, as_of: datetime, entry_ids: Sequence[int] | None, exclude_card_id: int | None
) -> list[ColumnElement[bool]]:
    conditions = [*_eligible(user_id), CardModel.due_at <= as_of]
    if entry_ids is not None:
        conditions.append(CardModel.vocab_entry_id.in_(list(entry_ids)))
    if exclude_card_id is not None:
        conditions.append(CardModel.id != exclude_card_id)
    return conditions


class SqlCardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, new_cards: Sequence[NewCard]) -> list[Card]:
        models = [
            CardModel(
                user_id=n.user_id,
                vocab_entry_id=n.vocab_entry_id,
                card_type=n.card_type.value,
                state=n.schedule.state.value,
                step=n.schedule.step,
                stability=n.schedule.stability,
                difficulty=n.schedule.difficulty,
                due_at=n.schedule.due_at,
                last_review_at=n.schedule.last_review_at,
                reps=0,
                lapses=0,
                is_suspended=False,
                created_at=n.created_at,
                updated_at=n.created_at,
            )
            for n in new_cards
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_card(m) for m in models]

    async def get(self, user_id: int, card_id: int) -> Card | None:
        model = (
            await self._session.execute(
                select(CardModel).where(CardModel.id == card_id, CardModel.user_id == user_id)
            )
        ).scalar_one_or_none()
        return _card(model) if model else None

    async def get_for_update(self, user_id: int, card_id: int) -> Card | None:
        model = (
            await self._session.execute(
                select(CardModel)
                .where(CardModel.id == card_id, CardModel.user_id == user_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        return _card(model) if model else None

    async def save(self, card: Card) -> None:
        s = card.schedule
        await self._session.execute(
            update(CardModel)
            .where(CardModel.id == card.id, CardModel.user_id == card.user_id)
            .values(
                state=s.state.value,
                step=s.step,
                stability=s.stability,
                difficulty=s.difficulty,
                due_at=s.due_at,
                last_review_at=s.last_review_at,
                reps=card.reps,
                lapses=card.lapses,
                is_suspended=card.is_suspended,
                updated_at=card.updated_at,
            )
        )

    async def list_due(
        self,
        user_id: int,
        now: datetime,
        limit: int,
        entry_ids: Sequence[int] | None,
        exclude_card_id: int | None,
    ) -> list[Card]:
        stmt = (
            select(CardModel)
            .where(*_due_conditions(user_id, now, entry_ids, exclude_card_id))
            .order_by(CardModel.due_at, CardModel.id)
            .limit(limit)
        )
        rows = await self._session.execute(stmt)
        return [_card(m) for m in rows.scalars()]

    async def count_due(
        self, user_id: int, as_of: datetime, entry_ids: Sequence[int] | None, exclude_card_id: int | None
    ) -> int:
        stmt = select(func.count(CardModel.id)).where(
            *_due_conditions(user_id, as_of, entry_ids, exclude_card_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_due_words(self, user_id: int, as_of: datetime) -> int:
        stmt = select(func.count(func.distinct(CardModel.vocab_entry_id))).where(
            *_due_conditions(user_id, as_of, None, None)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def next_due_after(self, user_id: int, now: datetime) -> datetime | None:
        stmt = select(func.min(CardModel.due_at)).where(*_eligible(user_id), CardModel.due_at > now)
        value: datetime | None = (await self._session.execute(stmt)).scalar_one()
        return value

    async def count_cards(self, user_id: int) -> int:
        stmt = select(func.count(CardModel.id)).where(CardModel.user_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_for_entry(self, user_id: int, vocab_entry_id: int) -> list[Card]:
        rows = await self._session.execute(
            select(CardModel)
            .where(CardModel.user_id == user_id, CardModel.vocab_entry_id == vocab_entry_id)
            .order_by(CardModel.id)
        )
        return [_card(m) for m in rows.scalars()]

    async def list_for_entries(self, user_id: int, vocab_entry_ids: Sequence[int]) -> list[Card]:
        if not vocab_entry_ids:
            return []
        rows = await self._session.execute(
            select(CardModel)
            .where(CardModel.user_id == user_id, CardModel.vocab_entry_id.in_(list(vocab_entry_ids)))
            .order_by(CardModel.id)
        )
        return [_card(m) for m in rows.scalars()]

    async def bury_siblings(
        self, user_id: int, vocab_entry_id: int, graded_card_id: int, now: datetime, until: datetime
    ) -> int:
        result = await self._session.execute(
            update(CardModel)
            .where(
                CardModel.user_id == user_id,
                CardModel.vocab_entry_id == vocab_entry_id,
                CardModel.id != graded_card_id,
                CardModel.is_suspended.is_(False),
                CardModel.due_at <= now,
            )
            .values(due_at=until, updated_at=now)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def reschedule_now(self, user_id: int, vocab_entry_ids: Sequence[int], now: datetime) -> int:
        if not vocab_entry_ids:
            return 0
        result = await self._session.execute(
            update(CardModel)
            .where(CardModel.user_id == user_id, CardModel.vocab_entry_id.in_(list(vocab_entry_ids)))
            .values(due_at=now, is_suspended=False, updated_at=now)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def search(self, flt: CardFilter, offset: int, limit: int) -> tuple[list[Card], int]:
        conds: list[ColumnElement[bool]] = [CardModel.user_id == flt.user_id]
        if flt.state is not None:
            conds.append(CardModel.state == flt.state.value)
        if flt.suspended is not None:
            conds.append(CardModel.is_suspended.is_(flt.suspended))
        if flt.due is not None:
            is_due = and_(*_due_conditions(flt.user_id, flt.now, None, None))
            conds.append(is_due if flt.due else not_(is_due))
        total = (await self._session.execute(select(func.count(CardModel.id)).where(*conds))).scalar_one()
        rows = await self._session.execute(
            select(CardModel)
            .where(*conds)
            .order_by(CardModel.due_at, CardModel.id)
            .offset(offset)
            .limit(limit)
        )
        return [_card(m) for m in rows.scalars()], int(total)

    async def summaries_for_entries(
        self, user_id: int, entry_ids: Sequence[int], now: datetime
    ) -> dict[int, EntrySrsSummary]:
        if not entry_ids:
            return {}
        due_flag = case((CardModel.is_suspended.is_(False) & (CardModel.due_at <= now), 1), else_=0)
        stmt = (
            select(
                CardModel.vocab_entry_id,
                func.count(CardModel.id),
                func.sum(due_flag),
                func.sum(CardModel.reps),
                func.min(CardModel.due_at).filter(CardModel.is_suspended.is_(False)),
            )
            .where(CardModel.user_id == user_id, CardModel.vocab_entry_id.in_(list(entry_ids)))
            .group_by(CardModel.vocab_entry_id)
        )
        return {
            entry_id: EntrySrsSummary(entry_id, int(count), int(due or 0), int(reps or 0), next_due)
            for entry_id, count, due, reps, next_due in (await self._session.execute(stmt)).all()
        }


class SqlReviewLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, new_log: NewReviewLog) -> ReviewLog:
        model = ReviewLogModel(
            card_id=new_log.card_id,
            user_id=new_log.user_id,
            rating=int(new_log.rating),
            state_before=new_log.state_before.value,
            stability_before=new_log.stability_before,
            stability_after=new_log.stability_after,
            difficulty_before=new_log.difficulty_before,
            difficulty_after=new_log.difficulty_after,
            due_after=new_log.due_after,
            duration_ms=new_log.duration_ms,
            presentation_id=new_log.presentation_id,
            reviewed_at=new_log.reviewed_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError as exc:
            raise PresentationIdTakenError() from exc
        return _log(model)

    async def find_by_presentation(self, presentation_id: uuid.UUID) -> ReviewLog | None:
        model = (
            await self._session.execute(
                select(ReviewLogModel).where(ReviewLogModel.presentation_id == presentation_id)
            )
        ).scalar_one_or_none()
        return _log(model) if model else None

    async def list_for_card(self, card_id: int, offset: int, limit: int) -> tuple[list[ReviewLog], int]:
        total = (
            await self._session.execute(
                select(func.count(ReviewLogModel.id)).where(ReviewLogModel.card_id == card_id)
            )
        ).scalar_one()
        rows = await self._session.execute(
            select(ReviewLogModel)
            .where(ReviewLogModel.card_id == card_id)
            .order_by(ReviewLogModel.reviewed_at.desc(), ReviewLogModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_log(m) for m in rows.scalars()], int(total)

    async def count_between(self, user_id: int, start: datetime, end: datetime) -> int:
        stmt = select(func.count(ReviewLogModel.id)).where(
            ReviewLogModel.user_id == user_id,
            ReviewLogModel.reviewed_at >= start,
            ReviewLogModel.reviewed_at < end,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_for_user(self, user_id: int) -> int:
        stmt = select(func.count(ReviewLogModel.id)).where(ReviewLogModel.user_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_recalled_for_user(self, user_id: int) -> int:
        stmt = select(func.count(ReviewLogModel.id)).where(
            ReviewLogModel.user_id == user_id, ReviewLogModel.rating > int(Rating.AGAIN)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_for_optimizer(self, user_id: int, limit: int) -> list[OptimizerLog]:
        rows = await self._session.execute(
            select(
                ReviewLogModel.card_id,
                ReviewLogModel.rating,
                ReviewLogModel.reviewed_at,
                ReviewLogModel.duration_ms,
            )
            .where(ReviewLogModel.user_id == user_id)
            .order_by(ReviewLogModel.reviewed_at.desc(), ReviewLogModel.id.desc())
            .limit(limit)
        )
        logs = [OptimizerLog(card_id, Rating(rating), at, ms) for card_id, rating, at, ms in rows.all()]
        logs.reverse()
        return logs
