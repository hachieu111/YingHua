"""Hiện thực `VocabCardSource` của M08 bằng dữ liệu M07 — thẻ lấy nội dung hai mặt và bộ thẻ từ đây."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library.application.public import PageAccessPort
from app.modules.review.application.public import ContextFace, DeckKind, DeckRef, EntryFace
from app.modules.vocab.application.ports import TermDictionary
from app.modules.vocab.infrastructure.repositories import SqlVocabContextRepository, SqlVocabRepository


class SqlVocabCardSource:
    """Dùng chung phiên (session) với giao dịch của M08 nên đọc nhất quán với thẻ đang xử lý."""

    def __init__(self, session: AsyncSession, dictionary: TermDictionary, pages: PageAccessPort) -> None:
        self._entries = SqlVocabRepository(session)
        self._contexts = SqlVocabContextRepository(session)
        self._dictionary = dictionary
        self._pages = pages

    async def faces(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, EntryFace]:
        entries = await self._entries.get_many(user_id, entry_ids)
        if not entries:
            return {}
        contexts = await self._contexts.summaries(list(entries))
        sino = await self._dictionary.sino_vietnamese([e.term for e in entries.values()])
        faces: dict[int, EntryFace] = {}
        for entry in entries.values():
            summary = contexts.get(entry.id)
            latest = summary.latest if summary else None
            faces[entry.id] = EntryFace(
                vocab_entry_id=entry.id,
                term=entry.term,
                pinyin=entry.pinyin,
                meaning_vi=entry.meaning_vi,
                sino_vietnamese=sino.get(entry.term),
                note=entry.note,
                status=entry.status.value,
                is_starred=entry.is_starred,
                hsk_level=entry.hsk_level,
                context=ContextFace(
                    latest.id,
                    latest.snippet_file_id,
                    latest.sentence_zh,
                    latest.sentence_vi,
                    latest.source_label,
                )
                if latest
                else None,
                contexts_count=summary.count if summary else 0,
            )
        return faces

    async def status_counts(self, user_id: int) -> dict[str, int]:
        return await self._entries.status_counts(user_id)

    async def entry_ids_for_deck(self, user_id: int, deck: DeckRef) -> list[int]:
        if deck.kind is DeckKind.STARRED:
            return await self._entries.starred_ids(user_id)
        if deck.kind is DeckKind.SERIES and deck.series_id is not None:
            page_ids = await self._pages.page_ids_of_series(deck.series_id)
            return await self._contexts.entry_ids_for_pages(user_id, page_ids)
        return []
