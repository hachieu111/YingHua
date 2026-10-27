from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reader.domain.grammar import (
    GrammarAnalysis,
    GrammarContent,
    content_from_json,
    content_to_json,
)
from app.modules.reader.infrastructure.orm_models import GrammarAnalysisModel, GrammarRequestModel


def _analysis(model: GrammarAnalysisModel) -> GrammarAnalysis | None:
    content = content_from_json(model.content)
    if content is None:  # dữ liệu hỏng coi như chưa có cache để phân tích lại
        return None
    return GrammarAnalysis(model.id, model.sentence_zh, content, model.model)


class SqlGrammarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, sentence_hash: str) -> GrammarAnalysis | None:
        model = (
            await self._session.execute(
                select(GrammarAnalysisModel).where(GrammarAnalysisModel.sentence_hash == sentence_hash)
            )
        ).scalar_one_or_none()
        return _analysis(model) if model else None

    async def add(
        self, sentence_hash: str, sentence: str, content: GrammarContent, model: str | None
    ) -> GrammarAnalysis:
        values = {"sentence_zh": sentence, "content": content_to_json(content), "model": model}
        # Hai người phân tích cùng một câu cùng lúc: kết quả hợp lệ sau cùng thay kết quả trước (cũng sửa
        # được bản ghi cũ bị hỏng), khóa UNIQUE bảo đảm mỗi câu chỉ có một dòng.
        analysis_id = (
            await self._session.execute(
                insert(GrammarAnalysisModel)
                .values(sentence_hash=sentence_hash, **values)
                .on_conflict_do_update(index_elements=[GrammarAnalysisModel.sentence_hash], set_=values)
                .returning(GrammarAnalysisModel.id)
            )
        ).scalar_one()
        return GrammarAnalysis(analysis_id, sentence, content, model)

    async def add_request(self, user_id: int, analysis_id: int | None, requested_at: datetime) -> None:
        self._session.add(
            GrammarRequestModel(user_id=user_id, analysis_id=analysis_id, requested_at=requested_at)
        )
        await self._session.flush()

    async def count_requests_between(self, user_id: int, start: datetime, end: datetime) -> int:
        stmt = select(func.count(GrammarRequestModel.id)).where(
            GrammarRequestModel.user_id == user_id,
            GrammarRequestModel.requested_at >= start,
            GrammarRequestModel.requested_at < end,
        )
        return int((await self._session.execute(stmt)).scalar_one())
