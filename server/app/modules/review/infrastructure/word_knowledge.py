"""Dữ liệu từ điển M06 cho Thẻ mở rộng AI dự phòng (F08.11): chiết tự, câu ví dụ, cụm đi kèm."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.glosses import best_gloss, short_meaning
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from app.modules.review.domain.ai_note import AiExample, AiPhrase, CharParts

EXAMPLE_MIN_CHARS = 5
EXAMPLE_MAX_CHARS = 25
PHRASE_GLOSS_MAX_CHARS = 60
PHRASE_GLOSS_LIMIT_SCAN = 1000  # rút gọn nghĩa nhưng không cắt, để biết nghĩa có quá dài không


def _is_han(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


class DictionaryWordKnowledge:
    """Đọc M06 qua phiên chỉ-đọc riêng, không đụng giao dịch của M08."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def char_parts(self, term: str) -> list[CharParts]:
        chars = list(dict.fromkeys(c for c in term if _is_han(c)))
        if not chars:
            return []
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            hanzi = await uow.reader.get_hanzi(chars)
        return [
            CharParts(c, info.han_viet, info.radical, tuple(info.components))
            for c in chars
            if (info := hanzi.get(c)) is not None and (info.components or info.radical or info.han_viet)
        ]

    async def examples(self, term: str, max_difficulty: int, limit: int) -> list[AiExample]:
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            tatoeba = await uow.reader.find_tatoeba_examples(term, max_difficulty, limit * 4)
            ids = await uow.reader.find_entry_ids([term])
            entry_id = ids.get(term)
            dictionary = (await uow.reader.get_examples([entry_id])).get(entry_id, []) if entry_id else []
        pool = [AiExample(e.zh, e.pinyin, e.vi) for e in tatoeba]
        pool += [AiExample(e.zh, e.pinyin, e.vi) for e in dictionary]
        usable = [e for e in pool if term in e.zh and EXAMPLE_MIN_CHARS <= len(e.zh) <= EXAMPLE_MAX_CHARS]
        usable.sort(key=lambda e: (e.vi is None, len(e.zh)))  # có bản dịch Việt và câu ngắn trước
        unique: dict[str, AiExample] = {}
        for example in usable:
            unique.setdefault(example.zh, example)
        return list(unique.values())[:limit]

    async def collocations(self, term: str, limit: int) -> list[AiPhrase]:
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            entries = await uow.reader.find_compounds(term, limit * 2)
        phrases: list[AiPhrase] = []
        for entry in entries:
            full = short_meaning(best_gloss(d.gloss for d in entry.definitions), PHRASE_GLOSS_LIMIT_SCAN)
            if not full or len(full) > PHRASE_GLOSS_MAX_CHARS:
                continue  # nghĩa dài (tên riêng, thuật ngữ) không hợp làm cụm đi kèm
            phrases.append(AiPhrase(entry.simplified, entry.pinyin, full))
        return phrases[:limit]
