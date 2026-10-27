"""Nguồn dữ liệu của F12.04, lấy qua giao diện công khai của M02, M07, M08, M10."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.application.public import Identity, Role
from app.modules.review.application.public import EstimateRetrievabilityUseCase
from app.modules.review.infrastructure.public import FsrsScheduler, SqlCardRepository
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork
from app.modules.stats.application.today_ports import WeakWords
from app.modules.suggestions.application.use_cases.list_suggestions import ListSuggestionsUseCase
from app.modules.vocab.infrastructure.public import SqlVocabQuizSource


class SettingsWeeklyGoalSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def weekly_page_goal(self, identity: Identity, owner_id: int) -> int | None:
        use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory))
        return (await use_case.execute(identity, owner_id)).weekly_page_goal


class ReviewWeakWordsSource:
    """Từ đủ điều kiện ra đề (M07) và R hiện tại của chúng (M08, cùng cách chọn từ của bài kiểm tra)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._estimate = EstimateRetrievabilityUseCase(FsrsScheduler())

    async def weak_words(self, user_id: int, threshold: float, now: datetime) -> WeakWords:
        async with self._session_factory() as session:
            pool = await SqlVocabQuizSource(session).quizzable_words(user_id)
            r_by_entry = await self._estimate.execute(
                SqlCardRepository(session), user_id, [w.entry_id for w in pool], now
            )
        return WeakWords(len(pool), sum(1 for r in r_by_entry.values() if r < threshold))


class SuggestionsChapterSource:
    def __init__(self, list_suggestions: ListSuggestionsUseCase) -> None:
        self._list = list_suggestions

    async def top_terms(self, identity: Identity, owner_id: int, chapter_id: int, limit: int) -> list[str]:
        # Gợi ý tính theo `identity.user_id`; quản trị viên xem của người khác thì dùng danh tính người đó
        # (chỉ đọc) để loại đúng từ họ đã lưu/bỏ qua.
        viewer = (
            identity if owner_id == identity.user_id else Identity(owner_id, Role.USER, identity.session_id)
        )
        result = await self._list.execute(viewer, chapter_id, limit)
        return [s.term for s in result.items]
