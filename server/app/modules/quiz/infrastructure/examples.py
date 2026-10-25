"""Câu ví dụ Tatoeba cho bài kiểm tra, đọc từ M06 qua giao diện công khai (F09.09)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.dictionary.application.public import TatoebaExample
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from app.modules.quiz.domain.entities import ExampleRow


def _row(e: TatoebaExample) -> ExampleRow:
    return ExampleRow(e.id, e.zh, e.pinyin, e.vi, e.difficulty_level)


class DictionaryExampleSource:
    """Mọi lời gọi chỉ đọc, dùng phiên riêng nên không ảnh hưởng giao dịch của bài kiểm tra."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def find(self, term: str, max_difficulty: int, limit: int) -> list[ExampleRow]:
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            found = await uow.reader.find_tatoeba_examples(term, max_difficulty, limit)
        return [_row(e) for e in found]

    async def get_many(self, example_ids: Sequence[int]) -> dict[int, ExampleRow]:
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            found = await uow.reader.get_tatoeba_examples(example_ids)
        return {i: _row(e) for i, e in found.items()}

    async def sample_translations(self, difficulty: int, exclude_ids: Sequence[int], limit: int) -> list[str]:
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            return await uow.reader.sample_translations(difficulty, exclude_ids, limit)
