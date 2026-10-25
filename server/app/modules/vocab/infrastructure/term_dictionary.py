"""Adapter tra từ điển của M07: gọi M06 qua giao diện công khai (cấp HSK F06.08, nghĩa, âm Hán Việt)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.dictionary.application.public import resolve_hsk
from app.modules.dictionary.infrastructure.public import PypinyinProvider, SqlDictionaryUnitOfWork
from app.modules.vocab.application.ports import TermInfo

MAX_MEANING_GLOSSES = 3
GLOSS_SEPARATOR = "; "


def _is_han(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


class DictionaryTermAdapter:
    """Mọi lời gọi chỉ đọc, dùng phiên riêng nên không ảnh hưởng giao dịch lưu từ."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._pinyin = PypinyinProvider()

    async def describe(self, term: str) -> TermInfo:
        chars = list(dict.fromkeys(c for c in term if _is_han(c)))
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            entries = await uow.reader.find_entries(term)
            hsk = resolve_hsk(term, await uow.reader.get_hsk_levels([term, *chars]))
        glosses = list(dict.fromkeys(d.gloss for e in entries for d in e.definitions if d.gloss))
        return TermInfo(
            entry_id=min((e.id for e in entries), default=None),
            pinyin=entries[0].pinyin if entries else (self._pinyin.to_pinyin(term) or None),
            meaning_vi=GLOSS_SEPARATOR.join(glosses[:MAX_MEANING_GLOSSES]) or None,
            hsk_level=hsk.level,
            hsk_source=hsk.source.value,
        )

    async def sino_vietnamese(self, terms: Sequence[str]) -> dict[str, str]:
        chars = sorted({c for term in terms for c in term if _is_han(c)})
        if not chars:
            return {}
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            hanzi = await uow.reader.get_hanzi(chars)
        result: dict[str, str] = {}
        for term in terms:
            han = [c for c in term if _is_han(c)]
            sounds = [hanzi[c].han_viet for c in han if c in hanzi and hanzi[c].han_viet]
            if han and len(sounds) == len(han):
                result[term] = " ".join(s for s in sounds if s)
        return result
