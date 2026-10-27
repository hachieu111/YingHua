from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stats.application.dto import ActivityTotals
from app.modules.stats.domain.activity import ActivityDelta, DayActivity
from app.modules.stats.infrastructure.orm_models import DailyActivityModel as Row

_STUDY_DAY = or_(Row.reviews_count > 0, Row.pages_read > 0)


def _day(row: Row) -> DayActivity:
    return DayActivity(
        row.activity_date,
        row.reviews_count,
        row.pages_read,
        row.words_saved,
        row.quizzes_done,
        row.study_seconds,
    )


class SqlActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: int, day: date, delta: ActivityDelta, now: datetime) -> None:
        stmt = insert(Row).values(
            user_id=user_id,
            activity_date=day,
            reviews_count=delta.reviews_count,
            pages_read=delta.pages_read,
            words_saved=delta.words_saved,
            quizzes_done=delta.quizzes_done,
            study_seconds=delta.study_seconds,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Row.user_id, Row.activity_date],
            set_={
                "reviews_count": Row.reviews_count + stmt.excluded.reviews_count,
                "pages_read": Row.pages_read + stmt.excluded.pages_read,
                "words_saved": Row.words_saved + stmt.excluded.words_saved,
                "quizzes_done": Row.quizzes_done + stmt.excluded.quizzes_done,
                "study_seconds": Row.study_seconds + stmt.excluded.study_seconds,
                "updated_at": now,
            },
        )
        await self._session.execute(stmt)

    async def between(self, user_id: int, start: date, end: date) -> list[DayActivity]:
        rows = await self._session.scalars(
            select(Row)
            .where(Row.user_id == user_id, Row.activity_date >= start, Row.activity_date <= end)
            .order_by(Row.activity_date)
        )
        return [_day(r) for r in rows]

    async def study_days(self, user_id: int) -> list[date]:
        rows = await self._session.scalars(
            select(Row.activity_date).where(Row.user_id == user_id, _STUDY_DAY).order_by(Row.activity_date)
        )
        return list(rows)

    async def lifetime_totals(self, user_id: int) -> ActivityDelta:
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(Row.reviews_count), 0),
                    func.coalesce(func.sum(Row.pages_read), 0),
                    func.coalesce(func.sum(Row.words_saved), 0),
                    func.coalesce(func.sum(Row.quizzes_done), 0),
                    func.coalesce(func.sum(Row.study_seconds), 0),
                ).where(Row.user_id == user_id)
            )
        ).one()
        return ActivityDelta(*(int(v) for v in row))

    async def system_totals(self, start: date, end: date) -> ActivityTotals:
        window = (Row.activity_date >= start, Row.activity_date <= end)
        row = (
            await self._session.execute(
                select(
                    func.count(func.distinct(Row.user_id)).filter(_STUDY_DAY),
                    func.coalesce(func.sum(Row.reviews_count), 0),
                    func.coalesce(func.sum(Row.pages_read), 0),
                    func.coalesce(func.sum(Row.words_saved), 0),
                    func.coalesce(func.sum(Row.quizzes_done), 0),
                    func.coalesce(func.sum(Row.study_seconds), 0),
                ).where(*window)
            )
        ).one()
        return ActivityTotals(*(int(v) for v in row))
