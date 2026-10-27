from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.core.stored_files import SqlStoredFileRepository
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.imaging.infrastructure.public import SqlBubbleRepository
from app.modules.reader.infrastructure.public import SqlBubbleEditRepository
from app.modules.review.infrastructure.public import SqlCardRepository
from app.modules.stats.infrastructure.public import SqlActivityRecorder
from app.modules.vocab.infrastructure.repositories import SqlVocabContextRepository, SqlVocabRepository
from app.modules.vocab.infrastructure.sentence_repository import SqlSavedSentenceRepository


class SqlVocabUnitOfWork(SqlAlchemyUnitOfWork):
    """Một phiên/giao dịch dùng chung cho mục từ, ngữ cảnh, thẻ (M08), tệp và bong bóng (M04).

    Chia sẻ giao dịch giữa M07 và M08 (F08.09): repository thẻ của M08 được tạo trên CÙNG phiên này, nên lưu
    từ + ngữ cảnh + ba thẻ commit hoặc hủy cùng nhau.
    """

    entries: SqlVocabRepository
    contexts: SqlVocabContextRepository
    cards: SqlCardRepository
    files: SqlStoredFileRepository
    bubbles: SqlBubbleRepository
    audit: SqlAuditLogRepository
    sentences: SqlSavedSentenceRepository
    edits: SqlBubbleEditRepository
    activity: SqlActivityRecorder

    def _init_repositories(self) -> None:
        self.entries = SqlVocabRepository(self.session)
        self.contexts = SqlVocabContextRepository(self.session)
        self.cards = SqlCardRepository(self.session)
        self.files = SqlStoredFileRepository(self.session)
        self.bubbles = SqlBubbleRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
        self.sentences = SqlSavedSentenceRepository(self.session)
        self.edits = SqlBubbleEditRepository(self.session)
        self.activity = SqlActivityRecorder(self.session)
