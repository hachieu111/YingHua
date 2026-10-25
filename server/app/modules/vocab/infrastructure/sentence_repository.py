"""Kho câu thoại đã lưu (F07.11). Mọi truy vấn lọc theo `user_id` của chủ sở hữu."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vocab.domain.entities import NewSavedSentence, SavedSentence
from app.modules.vocab.infrastructure.orm_models import SavedSentenceModel


def _sentence(m: SavedSentenceModel) -> SavedSentence:
    return SavedSentence(
        id=m.id,
        user_id=m.user_id,
        sentence_zh=m.sentence_zh,
        created_at=m.created_at,
        updated_at=m.updated_at,
        bubble_id=m.bubble_id,
        page_id=m.page_id,
        sentence_vi=m.sentence_vi,
        source_label=m.source_label,
        note=m.note,
    )


class SqlSavedSentenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, new: NewSavedSentence) -> SavedSentence | None:
        stmt = (
            insert(SavedSentenceModel)
            .values(
                user_id=new.user_id,
                bubble_id=new.bubble_id,
                page_id=new.page_id,
                sentence_zh=new.sentence_zh,
                sentence_vi=new.sentence_vi,
                source_label=new.source_label,
                note=new.note,
                created_at=new.created_at,
                updated_at=new.created_at,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "bubble_id"])
            .returning(SavedSentenceModel)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _sentence(model) if model else None

    async def get(self, user_id: int, sentence_id: int) -> SavedSentence | None:
        model = (
            await self._session.execute(
                select(SavedSentenceModel).where(
                    SavedSentenceModel.id == sentence_id, SavedSentenceModel.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        return _sentence(model) if model else None

    async def get_by_bubble(self, user_id: int, bubble_id: int) -> SavedSentence | None:
        model = (
            await self._session.execute(
                select(SavedSentenceModel).where(
                    SavedSentenceModel.user_id == user_id, SavedSentenceModel.bubble_id == bubble_id
                )
            )
        ).scalar_one_or_none()
        return _sentence(model) if model else None

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[SavedSentence], int]:
        total = (
            await self._session.execute(
                select(func.count(SavedSentenceModel.id)).where(SavedSentenceModel.user_id == user_id)
            )
        ).scalar_one()
        rows = await self._session.execute(
            select(SavedSentenceModel)
            .where(SavedSentenceModel.user_id == user_id)
            .order_by(SavedSentenceModel.created_at.desc(), SavedSentenceModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_sentence(m) for m in rows.scalars()], int(total)

    async def update_note(self, user_id: int, sentence_id: int, note: str | None, now: datetime) -> None:
        await self._session.execute(
            update(SavedSentenceModel)
            .where(SavedSentenceModel.id == sentence_id, SavedSentenceModel.user_id == user_id)
            .values(note=note, updated_at=now)
        )

    async def delete(self, user_id: int, sentence_id: int) -> None:
        await self._session.execute(
            delete(SavedSentenceModel).where(
                SavedSentenceModel.id == sentence_id, SavedSentenceModel.user_id == user_id
            )
        )
