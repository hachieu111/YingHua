"""Tra `entry_id` từ điển (M06) cho các từ đã tách trong bong bóng, qua hàm công khai của M06."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.dictionary.application.public import FindEntryIdsUseCase
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork


class EntryIdLookup(Protocol):
    async def find_entry_ids(self, words: Sequence[str]) -> dict[str, int | None]:
        """Mã mục từ (nhỏ nhất, khớp giản thể) cho mỗi từ; None nếu không có."""
        ...


class SqlEntryIdLookup:
    """Lắp `FindEntryIdsUseCase` của M06 với CSDL; một truy vấn theo lô cho mọi từ."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._use_case = FindEntryIdsUseCase(lambda: SqlDictionaryUnitOfWork(session_factory))

    async def find_entry_ids(self, words: Sequence[str]) -> dict[str, int | None]:
        wanted = list(dict.fromkeys(w for w in words if w))
        found = await self._use_case.execute(wanted)
        return {word: found.get(word) for word in wanted}
