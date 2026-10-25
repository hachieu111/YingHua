from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.core.stored_files import SqlStoredFileRepository
from app.modules.auth.infrastructure.repositories import (
    SqlPasswordResetRepository,
    SqlSessionRepository,
    SqlUserRepository,
)


class SqlAuthUnitOfWork(SqlAlchemyUnitOfWork):
    users: SqlUserRepository
    sessions: SqlSessionRepository
    resets: SqlPasswordResetRepository
    files: SqlStoredFileRepository

    def _init_repositories(self) -> None:
        self.users = SqlUserRepository(self.session)
        self.sessions = SqlSessionRepository(self.session)
        self.resets = SqlPasswordResetRepository(self.session)
        self.files = SqlStoredFileRepository(self.session)
