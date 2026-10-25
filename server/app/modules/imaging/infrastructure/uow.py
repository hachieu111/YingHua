from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.core.stored_files import SqlStoredFileRepository
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.imaging.infrastructure.repositories import SqlBubbleRepository, SqlTranslationRepository


class SqlImagingUnitOfWork(SqlAlchemyUnitOfWork):
    translations: SqlTranslationRepository
    bubbles: SqlBubbleRepository
    files: SqlStoredFileRepository
    audit: SqlAuditLogRepository

    def _init_repositories(self) -> None:
        self.translations = SqlTranslationRepository(self.session)
        self.bubbles = SqlBubbleRepository(self.session)
        self.files = SqlStoredFileRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
