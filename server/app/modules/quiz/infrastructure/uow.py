from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.quiz.application.ports import ExampleSource, QuizVocabSource
from app.modules.quiz.infrastructure.repositories import SqlQuizRepository
from app.modules.review.infrastructure.public import SqlCardRepository
from app.modules.stats.infrastructure.public import SqlActivityRecorder

VocabSourceFactory = Callable[[AsyncSession], QuizVocabSource]


class SqlQuizUnitOfWork(SqlAlchemyUnitOfWork):
    """Giao dịch của M09. `vocab` do tầng lắp ghép cung cấp (M07 hiện thực); thẻ (M08) và nhật ký quản trị
    dùng chung phiên nên nộp bài, ôn sớm và đổi trạng thái từ commit hoặc hủy cùng nhau (F09.04).
    """

    quizzes: SqlQuizRepository
    vocab: QuizVocabSource
    cards: SqlCardRepository
    audit: SqlAuditLogRepository
    examples: ExampleSource
    activity: SqlActivityRecorder

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        vocab_factory: VocabSourceFactory,
        examples: ExampleSource,
    ) -> None:
        super().__init__(session_factory)
        self._vocab_factory = vocab_factory
        self.examples = examples

    def _init_repositories(self) -> None:
        self.quizzes = SqlQuizRepository(self.session)
        self.vocab = self._vocab_factory(self.session)
        self.cards = SqlCardRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
        self.activity = SqlActivityRecorder(self.session)
