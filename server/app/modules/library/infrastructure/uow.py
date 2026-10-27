from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.core.stored_files import SqlStoredFileRepository
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.imaging.infrastructure.public import SqlTranslationRepository
from app.modules.library.infrastructure.chapter_repository import SqlChapterRepository
from app.modules.library.infrastructure.page_repository import SqlPageRepository
from app.modules.library.infrastructure.progress_repository import SqlProgressRepository
from app.modules.library.infrastructure.repositories import SqlLibraryRepository, SqlRatingRepository
from app.modules.library.infrastructure.series_repository import SqlSeriesRepository
from app.modules.stats.infrastructure.public import SqlActivityRecorder


class SqlLibraryUnitOfWork(SqlAlchemyUnitOfWork):
    series: SqlSeriesRepository
    chapters: SqlChapterRepository
    pages: SqlPageRepository
    progress: SqlProgressRepository
    library: SqlLibraryRepository
    ratings: SqlRatingRepository
    files: SqlStoredFileRepository
    translations: SqlTranslationRepository
    audit: SqlAuditLogRepository
    activity: SqlActivityRecorder

    def _init_repositories(self) -> None:
        self.series = SqlSeriesRepository(self.session)
        self.chapters = SqlChapterRepository(self.session)
        self.pages = SqlPageRepository(self.session)
        self.progress = SqlProgressRepository(self.session)
        self.library = SqlLibraryRepository(self.session)
        self.ratings = SqlRatingRepository(self.session)
        self.files = SqlStoredFileRepository(self.session)
        self.translations = SqlTranslationRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
        self.activity = SqlActivityRecorder(self.session)
