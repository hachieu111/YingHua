"""Độ khó câu theo bảng HSK (jieba + `hsk_words`), dùng chung cho M08 (Thẻ mở rộng AI) và M09 (câu LLM)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.dictionary.domain.difficulty import example_difficulty
from app.modules.dictionary.infrastructure.text_tools import JiebaTokenizer
from app.modules.dictionary.infrastructure.uow import SqlDictionaryUnitOfWork


class JiebaExampleLevelChecker:
    """Độ khó câu do LLM viết: tách từ bằng jieba rồi lấy cấp HSK cao nhất theo bảng M06 (F06.04, F09.09)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._tokenizer = JiebaTokenizer()

    async def difficulties(self, sentences: Sequence[str]) -> list[int | None]:
        tokens = [await self._tokenizer.tokenize(s) for s in sentences]
        words = {t for ts in tokens for t in ts if t}
        chars = {c for w in words for c in w}
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            levels = await uow.reader.get_hsk_levels([*words, *chars])
        return [example_difficulty(ts, levels) for ts in tokens]
