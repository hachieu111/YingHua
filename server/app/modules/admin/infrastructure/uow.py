from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.repositories import SqlAuditLogRepository
from app.modules.auth.infrastructure.public import SqlSessionRepository, SqlUserRepository


class SqlAdminUnitOfWork(SqlAlchemyUnitOfWork):
    """Một giao dịch cho người dùng, phiên đăng nhập và nhật ký quản trị (F13.06)."""

    users: SqlUserRepository
    sessions: SqlSessionRepository
    audit: SqlAuditLogRepository

    def _init_repositories(self) -> None:
        self.users = SqlUserRepository(self.session)
        self.sessions = SqlSessionRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
