from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.audit_log_reader import SqlAuditLogReader
from app.modules.admin.infrastructure.moderation_repository import SqlModerationRepository
from app.modules.admin.infrastructure.repositories import SqlAuditLogRepository
from app.modules.admin.infrastructure.system_settings_repository import SqlSystemSettingsRepository
from app.modules.auth.infrastructure.public import SqlSessionRepository, SqlUserRepository


class SqlAdminUnitOfWork(SqlAlchemyUnitOfWork):
    """Một giao dịch cho người dùng, phiên đăng nhập và nhật ký quản trị (F13.06)."""

    users: SqlUserRepository
    sessions: SqlSessionRepository
    audit: SqlAuditLogRepository
    audit_logs: SqlAuditLogReader
    system_settings: SqlSystemSettingsRepository
    moderation: SqlModerationRepository

    def _init_repositories(self) -> None:
        self.users = SqlUserRepository(self.session)
        self.sessions = SqlSessionRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
        self.audit_logs = SqlAuditLogReader(self.session)
        self.system_settings = SqlSystemSettingsRepository(self.session)
        self.moderation = SqlModerationRepository(self.session)
