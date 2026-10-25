"""Hiện thực `SavedTermSource` của M10: từ nào người học đã có trong sổ tay (mọi trạng thái)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vocab.infrastructure.orm_models import VocabEntryModel


class SqlVocabSuggestionSource:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def saved_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        """Tập con của `terms` đã có trong sổ tay của người dùng, kể cả "Đã thuộc" và "Bỏ qua" (F10.01)."""
        if not terms:
            return set()
        rows = await self._session.execute(
            select(VocabEntryModel.term).where(
                VocabEntryModel.user_id == user_id, VocabEntryModel.term.in_(list(set(terms)))
            )
        )
        return set(rows.scalars())
