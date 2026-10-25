from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.settings.infrastructure.repositories import SqlSettingsRepository


class SqlSettingsUnitOfWork(SqlAlchemyUnitOfWork):
    settings: SqlSettingsRepository
    audit: SqlAuditLogRepository

    def _init_repositories(self) -> None:
        self.settings = SqlSettingsRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
