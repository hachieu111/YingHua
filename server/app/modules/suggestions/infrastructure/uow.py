from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.dictionary.infrastructure.public import SqlLookupEventRepository
from app.modules.imaging.infrastructure.public import SqlBubbleRepository
from app.modules.suggestions.infrastructure.repositories import SqlDismissedRepository
from app.modules.vocab.infrastructure.public import SqlVocabSuggestionSource


class SqlSuggestionUnitOfWork(SqlAlchemyUnitOfWork):
    """Một phiên đọc bong bóng (M04), sổ tay (M07), lịch sử tra (M06) và danh sách bỏ qua của M10."""

    dismissed: SqlDismissedRepository
    bubbles: SqlBubbleRepository
    saved: SqlVocabSuggestionSource
    lookups: SqlLookupEventRepository

    def _init_repositories(self) -> None:
        self.dismissed = SqlDismissedRepository(self.session)
        self.bubbles = SqlBubbleRepository(self.session)
        self.saved = SqlVocabSuggestionSource(self.session)
        self.lookups = SqlLookupEventRepository(self.session)
