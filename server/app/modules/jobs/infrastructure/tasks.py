"""Các tác vụ định kỳ cụ thể: gọi use case công khai của module sở hữu dữ liệu (F15.01, F15.02, F15.03)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.core.storage import FileStorage
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.application.public import PurgeExpiredSessionsUseCase
from app.modules.auth.infrastructure.public import SqlAuthUnitOfWork
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.application.worker import PurgeOrphanResultFilesUseCase
from app.modules.imaging.infrastructure.public import SqlImagingUnitOfWork
from app.modules.jobs.application.ports import JobsUnitOfWork, JobTask
from app.modules.jobs.application.public import JobRunner
from app.modules.jobs.application.use_cases.run_due_jobs import RunDueJobsUseCase
from app.modules.jobs.domain.entities import (
    CLEANUP_ORPHAN_FILES,
    CLEANUP_QUICK_UPLOADS,
    CLEANUP_SESSIONS,
    ORPHAN_FILES_INTERVAL_SECONDS,
    SESSIONS_INTERVAL_SECONDS,
    JobDefinition,
)
from app.modules.jobs.infrastructure.uow import SqlJobsUnitOfWork
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.application.public import PurgeExpiredQuickUploadsUseCase
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.application.public import PurgeExpiredGuestSessionsUseCase
from app.modules.reader.infrastructure.public import SqlReaderUnitOfWork


class CleanupQuickUploadsTask:
    """F15.01 — Dọn ảnh tải nhanh hết hạn."""

    def __init__(self, purge: PurgeExpiredQuickUploadsUseCase) -> None:
        self._purge = purge

    async def run(self, now: datetime) -> dict[str, Any]:
        report = await self._purge.execute(now)
        return {"pages": report.pages, "files": report.files}


class CleanupSessionsTask:
    """F15.02 — Dọn phiên đăng nhập, liên kết đặt lại mật khẩu và phiên Khách hết hạn."""

    def __init__(
        self, sessions: PurgeExpiredSessionsUseCase, guests: PurgeExpiredGuestSessionsUseCase
    ) -> None:
        self._sessions = sessions
        self._guests = guests

    async def run(self, now: datetime) -> dict[str, Any]:
        report = await self._sessions.execute(now)
        return {
            "refresh_tokens": report.refresh_tokens,
            "reset_tokens": report.reset_tokens,
            "guest_sessions": await self._guests.execute(now),
        }


class CleanupOrphanFilesTask:
    """F15.03 — Dọn ảnh dẫn xuất mồ côi do worker lưu mà không hoàn tất."""

    def __init__(self, purge: PurgeOrphanResultFilesUseCase) -> None:
        self._purge = purge

    async def run(self, now: datetime) -> dict[str, Any]:
        return {"files": await self._purge.execute(now)}


def default_job_definitions(cleanup_interval_minutes: int) -> list[JobDefinition]:
    """Danh sách tác vụ mặc định; chu kỳ dọn ảnh tải nhanh lấy từ Settings (mặc định 60 phút)."""
    return [
        JobDefinition(CLEANUP_QUICK_UPLOADS, cleanup_interval_minutes * 60),
        JobDefinition(CLEANUP_SESSIONS, SESSIONS_INTERVAL_SECONDS),
        JobDefinition(CLEANUP_ORPHAN_FILES, ORPHAN_FILES_INTERVAL_SECONDS),
    ]


def build_job_tasks(
    session_factory: async_sessionmaker[AsyncSession], storage: FileStorage
) -> dict[str, JobTask]:
    def library_uow() -> LibraryUnitOfWork:
        return SqlLibraryUnitOfWork(session_factory)

    def auth_uow() -> AuthUnitOfWork:
        return SqlAuthUnitOfWork(session_factory)

    def reader_uow() -> ReaderUnitOfWork:
        return SqlReaderUnitOfWork(session_factory)

    def imaging_uow() -> ImagingUnitOfWork:
        return SqlImagingUnitOfWork(session_factory)

    return {
        CLEANUP_QUICK_UPLOADS: CleanupQuickUploadsTask(PurgeExpiredQuickUploadsUseCase(library_uow, storage)),
        CLEANUP_SESSIONS: CleanupSessionsTask(
            PurgeExpiredSessionsUseCase(auth_uow), PurgeExpiredGuestSessionsUseCase(reader_uow)
        ),
        CLEANUP_ORPHAN_FILES: CleanupOrphanFilesTask(PurgeOrphanResultFilesUseCase(imaging_uow, storage)),
    }


def build_job_runner(
    session_factory: async_sessionmaker[AsyncSession],
    storage: FileStorage,
    clock: Clock,
    cleanup_interval_minutes: int,
) -> JobRunner:
    """Lắp `JobRunner` cho worker: `await runner.run_due_jobs(clock.now(), worker_id)`."""

    def jobs_uow() -> JobsUnitOfWork:
        return SqlJobsUnitOfWork(session_factory)

    return JobRunner(
        RunDueJobsUseCase(
            jobs_uow,
            clock,
            default_job_definitions(cleanup_interval_minutes),
            build_job_tasks(session_factory, storage),
        )
    )
