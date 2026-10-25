from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.dictionary.infrastructure.repositories import (
    SqlDictionaryReader,
    SqlDictionaryWriter,
    SqlLookupEventRepository,
)


class SqlDictionaryUnitOfWork(SqlAlchemyUnitOfWork):
    reader: SqlDictionaryReader
    writer: SqlDictionaryWriter
    events: SqlLookupEventRepository

    def _init_repositories(self) -> None:
        self.reader = SqlDictionaryReader(self.session)
        self.writer = SqlDictionaryWriter(self.session)
        self.events = SqlLookupEventRepository(self.session)
