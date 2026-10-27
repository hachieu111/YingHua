from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.glosses import best_gloss
from app.modules.dictionary.application.public import resolve_hsk
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from app.modules.quiz.domain.entities import QuizWord
from app.modules.quiz.domain.rules import option_meaning


class DictionaryTermFacts:
    """Pinyin, nghĩa ngắn và cấp HSK của một từ lấy từ M06 (F09.10), không phụ thuộc sổ tay của người học."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def facts(self, term: str) -> QuizWord | None:
        async with SqlDictionaryUnitOfWork(self._session_factory) as dic:
            entry = (await dic.reader.brief_entries([term])).get(term)
            levels = await dic.reader.get_hsk_levels([term, *term])
        level = resolve_hsk(term, levels).level
        if entry is None and level is None:
            return None
        meaning = option_meaning(best_gloss(d.gloss for d in entry.definitions)) if entry else ""
        return QuizWord(0, term, entry.pinyin if entry else None, meaning or None, level, "")
