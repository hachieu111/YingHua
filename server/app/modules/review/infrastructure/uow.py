from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.review.application.ports import VocabCardSource
from app.modules.review.infrastructure.ai_note_repository import SqlAiNoteRepository
from app.modules.review.infrastructure.fsrs_profile_repository import SqlFsrsProfileRepository
from app.modules.review.infrastructure.repositories import SqlCardRepository, SqlReviewLogRepository
from app.modules.stats.infrastructure.public import SqlActivityRecorder

VocabSourceFactory = Callable[[AsyncSession], VocabCardSource]


class SqlReviewUnitOfWork(SqlAlchemyUnitOfWork):
    """Giao dịch của M08. `vocab` do tầng lắp ghép cung cấp (M07 hiện thực) và dùng chung phiên."""

    cards: SqlCardRepository
    logs: SqlReviewLogRepository
    vocab: VocabCardSource
    audit: SqlAuditLogRepository
    ai_notes: SqlAiNoteRepository
    fsrs_profiles: SqlFsrsProfileRepository
    activity: SqlActivityRecorder

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], vocab_factory: VocabSourceFactory
    ) -> None:
        super().__init__(session_factory)
        self._vocab_factory = vocab_factory

    def _init_repositories(self) -> None:
        self.cards = SqlCardRepository(self.session)
        self.logs = SqlReviewLogRepository(self.session)
        self.vocab = self._vocab_factory(self.session)
        self.audit = SqlAuditLogRepository(self.session)
        self.ai_notes = SqlAiNoteRepository(self.session)
        self.fsrs_profiles = SqlFsrsProfileRepository(self.session)
        self.activity = SqlActivityRecorder(self.session)
