"""Kho bộ đệm Thẻ mở rộng AI (F08.11)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, column, func, select, table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.review.domain.ai_note import AiNote, AiNoteContent, AiNoteSource
from app.modules.review.infrastructure.orm_models import VocabAiNoteModel

# Tham chiếu chỉ-đọc tới bảng mục từ của M07 (hợp đồng lược đồ) để đếm hạn mức theo người học.
_ENTRIES = table("vocab_entries", column("id", BigInteger), column("user_id", BigInteger))


def _note(m: VocabAiNoteModel) -> AiNote:
    return AiNote(
        vocab_entry_id=m.vocab_entry_id,
        content=AiNoteContent.from_json(m.content),
        source=AiNoteSource(m.source),
        generated_at=m.generated_at,
        regenerate_count=m.regenerate_count,
        model=m.model,
    )


class SqlAiNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, vocab_entry_id: int) -> AiNote | None:
        model = await self._session.get(VocabAiNoteModel, vocab_entry_id)
        return _note(model) if model else None

    async def save(self, note: AiNote) -> None:
        values = {
            "vocab_entry_id": note.vocab_entry_id,
            "content": note.content.to_json(),
            "model": note.model,
            "source": note.source.value,
            "generated_at": note.generated_at,
            "regenerate_count": note.regenerate_count,
        }
        stmt = insert(VocabAiNoteModel).values(**values)
        update = {k: v for k, v in values.items() if k != "vocab_entry_id"}
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=["vocab_entry_id"], set_=update)
        )

    async def count_llm_between(self, user_id: int, start: datetime, end: datetime) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(VocabAiNoteModel)
            .join(_ENTRIES, _ENTRIES.c.id == VocabAiNoteModel.vocab_entry_id)
            .where(
                _ENTRIES.c.user_id == user_id,
                VocabAiNoteModel.source == AiNoteSource.LLM.value,
                VocabAiNoteModel.generated_at >= start,
                VocabAiNoteModel.generated_at < end,
            )
        )
        return int(count or 0)
