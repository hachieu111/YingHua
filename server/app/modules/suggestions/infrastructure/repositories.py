from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.suggestions.domain.entities import DismissedTerm
from app.modules.suggestions.infrastructure.orm_models import DismissedSuggestionModel


class SqlDismissedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def terms(self, user_id: int) -> set[str]:
        rows = await self._session.execute(
            select(DismissedSuggestionModel.term).where(DismissedSuggestionModel.user_id == user_id)
        )
        return set(rows.scalars())

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[DismissedTerm], int]:
        total = (
            await self._session.execute(
                select(func.count())
                .select_from(DismissedSuggestionModel)
                .where(DismissedSuggestionModel.user_id == user_id)
            )
        ).scalar_one()
        rows = await self._session.execute(
            select(DismissedSuggestionModel.term, DismissedSuggestionModel.dismissed_at)
            .where(DismissedSuggestionModel.user_id == user_id)
            .order_by(DismissedSuggestionModel.dismissed_at.desc(), DismissedSuggestionModel.term)
            .offset(offset)
            .limit(limit)
        )
        return [DismissedTerm(term, at) for term, at in rows.all()], int(total)

    async def add(self, user_id: int, term: str, now: datetime) -> None:
        await self._session.execute(
            insert(DismissedSuggestionModel)
            .values(user_id=user_id, term=term, dismissed_at=now)
            .on_conflict_do_nothing(index_elements=["user_id", "term"])
        )

    async def remove(self, user_id: int, term: str) -> None:
        await self._session.execute(
            delete(DismissedSuggestionModel).where(
                DismissedSuggestionModel.user_id == user_id, DismissedSuggestionModel.term == term
            )
        )
