from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.dictionary.infrastructure.repositories import (
    SqlDictionaryReader,
    SqlDictionaryWriter,
    SqlLookupEventRepository,
)
from app.modules.gamification.infrastructure.public import SqlLearningEvents


class SqlDictionaryUnitOfWork(SqlAlchemyUnitOfWork):
    reader: SqlDictionaryReader
    writer: SqlDictionaryWriter
    events: SqlLookupEventRepository
    learning: SqlLearningEvents

    def _init_repositories(self) -> None:
        self.reader = SqlDictionaryReader(self.session)
        self.writer = SqlDictionaryWriter(self.session)
        self.events = SqlLookupEventRepository(self.session)
        self.learning = SqlLearningEvents(self.session)  # huy hiệu tức thời của M16 (F16.11)
