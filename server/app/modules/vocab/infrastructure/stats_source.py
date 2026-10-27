"""Số liệu sổ tay (M07) cho thống kê toàn hệ thống (F12.03): chỉ đếm, không đọc nội dung."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.stats.application.dto import VocabCounts
from app.modules.vocab.infrastructure.orm_models import VocabEntryModel


class SqlVocabCountsSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def vocab_counts(self) -> VocabCounts:
        async with self._session_factory() as session:
            entries = (await session.execute(select(func.count()).select_from(VocabEntryModel))).scalar_one()
        return VocabCounts(int(entries))
