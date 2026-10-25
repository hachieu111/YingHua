"""Hiện thực `QuizVocabSource` của M09 bằng dữ liệu M07 — bài kiểm tra chọn từ và ôn lại từ sai qua đây."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quiz.application.public import EntryRef, QuizWord, WordContext
from app.modules.vocab.domain.entities import VocabStatus
from app.modules.vocab.infrastructure.orm_models import VocabContextModel, VocabEntryModel


class SqlVocabQuizSource:
    """Dùng chung phiên với giao dịch của M09 nên đổi trạng thái từ commit cùng với thẻ và điểm bài."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def quizzable_words(self, user_id: int) -> list[QuizWord]:
        rows = await self._session.execute(
            select(
                VocabEntryModel.id,
                VocabEntryModel.term,
                VocabEntryModel.pinyin,
                VocabEntryModel.meaning_vi,
                VocabEntryModel.hsk_level,
                VocabEntryModel.status,
            )
            .where(VocabEntryModel.user_id == user_id, VocabEntryModel.status != VocabStatus.IGNORED.value)
            .order_by(VocabEntryModel.id)
        )
        return [QuizWord(*row) for row in rows.all()]

    async def contexts(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, list[WordContext]]:
        if not entry_ids:
            return {}
        rows = await self._session.execute(
            select(
                VocabContextModel.vocab_entry_id, VocabContextModel.sentence_zh, VocabContextModel.sentence_vi
            )
            .join(VocabEntryModel, VocabEntryModel.id == VocabContextModel.vocab_entry_id)
            .where(VocabEntryModel.user_id == user_id, VocabContextModel.vocab_entry_id.in_(list(entry_ids)))
            .order_by(VocabContextModel.created_at.desc(), VocabContextModel.id.desc())
        )
        result: dict[int, list[WordContext]] = {}
        for entry_id, sentence_zh, sentence_vi in rows.all():
            result.setdefault(entry_id, []).append(WordContext(sentence_zh, sentence_vi))
        return result

    async def entries(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, EntryRef]:
        if not entry_ids:
            return {}
        rows = await self._session.execute(
            select(VocabEntryModel.id, VocabEntryModel.term, VocabEntryModel.status).where(
                VocabEntryModel.user_id == user_id, VocabEntryModel.id.in_(list(entry_ids))
            )
        )
        return {entry_id: EntryRef(entry_id, term, status) for entry_id, term, status in rows.all()}

    async def saved_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        if not terms:
            return set()
        rows = await self._session.execute(
            select(VocabEntryModel.term).where(
                VocabEntryModel.user_id == user_id, VocabEntryModel.term.in_(list(set(terms)))
            )
        )
        return set(rows.scalars())

    async def mark_learning(self, user_id: int, entry_ids: Sequence[int], now: datetime) -> None:
        if not entry_ids:
            return
        await self._session.execute(
            update(VocabEntryModel)
            .where(
                VocabEntryModel.user_id == user_id,
                VocabEntryModel.id.in_(list(entry_ids)),
                VocabEntryModel.status == VocabStatus.KNOWN.value,
            )
            .values(status=VocabStatus.LEARNING.value, updated_at=now)
        )
