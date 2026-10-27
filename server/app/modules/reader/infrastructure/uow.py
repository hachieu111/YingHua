from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.imaging.infrastructure.public import SqlBubbleRepository, SqlTranslationRepository
from app.modules.reader.infrastructure.grammar_repository import SqlGrammarRepository
from app.modules.reader.infrastructure.repositories import (
    SqlAnnotationRepository,
    SqlBubbleEditRepository,
    SqlGuestSessionRepository,
)


class SqlReaderUnitOfWork(SqlAlchemyUnitOfWork):
    edits: SqlBubbleEditRepository
    annotations: SqlAnnotationRepository
    guests: SqlGuestSessionRepository
    bubbles: SqlBubbleRepository
    translations: SqlTranslationRepository
    audit: SqlAuditLogRepository
    grammar: SqlGrammarRepository

    def _init_repositories(self) -> None:
        self.grammar = SqlGrammarRepository(self.session)
        self.edits = SqlBubbleEditRepository(self.session)
        self.annotations = SqlAnnotationRepository(self.session)
        self.guests = SqlGuestSessionRepository(self.session)
        self.bubbles = SqlBubbleRepository(self.session)
        self.translations = SqlTranslationRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
