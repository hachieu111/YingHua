"""Các tác vụ định kỳ cụ thể: gọi use case công khai của module sở hữu dữ liệu (F15.01, F15.02, F15.03)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.core.storage import FileStorage
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.application.public import PurgeExpiredSessionsUseCase
from app.modules.auth.infrastructure.public import SqlAuthUnitOfWork
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.application.public import (
    EvaluateAchievementsUseCase,
    FinalizeSeasonsUseCase,
    PurgeMinigameRoundsUseCase,
)
from app.modules.gamification.infrastructure.public import SqlGamificationUnitOfWork, build_notice_sender
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
    EVALUATE_ACHIEVEMENTS,
    EVALUATE_ACHIEVEMENTS_INTERVAL_SECONDS,
    FINALIZE_SEASONS,
    FINALIZE_SEASONS_INTERVAL_SECONDS,
    OPTIMIZE_FSRS,
    ORPHAN_FILES_INTERVAL_SECONDS,
    PURGE_MINIGAME_ROUNDS,
    PURGE_MINIGAME_ROUNDS_INTERVAL_SECONDS,
    REMIND_VIP_EXPIRY,
    SEND_REMINDERS,
    SESSIONS_INTERVAL_SECONDS,
    VIP_REMINDER_INTERVAL_SECONDS,
    JobDefinition,
)
from app.modules.jobs.infrastructure.uow import SqlJobsUnitOfWork
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.application.public import LibraryPageAccess, PurgeExpiredQuickUploadsUseCase
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.application.public import ReminderConfig, SendDueRemindersUseCase
from app.modules.notifications.infrastructure.public import FileOutboxEmailSender, SqlNotificationsUnitOfWork
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.application.public import PurgeExpiredGuestSessionsUseCase
from app.modules.reader.infrastructure.public import SqlReaderUnitOfWork
from app.modules.review.application.ports import ReviewUnitOfWork, VocabCardSource
from app.modules.review.application.use_cases.optimize_fsrs_parameters import (
    OptimizeConfig,
    OptimizeFsrsParametersUseCase,
)
from app.modules.review.infrastructure.public import FsrsLibraryOptimizer, SqlDueCardCounter
from app.modules.review.infrastructure.uow import SqlReviewUnitOfWork
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.public import RemindVipExpiryUseCase
from app.modules.rewards.infrastructure.public import SqlRewardsUnitOfWork, build_reward_notifier
from app.modules.vocab.infrastructure.public import DictionaryTermAdapter, SqlVocabCardSource


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


class OptimizeFsrsTask:
    """F08.08 — Tối ưu tham số FSRS riêng cho từng người học."""

    def __init__(self, optimize: OptimizeFsrsParametersUseCase) -> None:
        self._optimize = optimize

    async def run(self, now: datetime) -> dict[str, Any]:
        return dict((await self._optimize.execute(now)).as_summary())


class SendRemindersTask:
    """F14.04 — Quét và gửi nhắc ôn hằng ngày."""

    def __init__(self, reminders: SendDueRemindersUseCase) -> None:
        self._reminders = reminders

    async def run(self, now: datetime) -> dict[str, Any]:
        return dict((await self._reminders.execute(now)).as_summary())


class RemindVipExpiryTask:
    """F17.03, US-HG-06 — Nhắc người học có VIP sắp hết hạn trong 24 giờ tới."""

    def __init__(self, remind: RemindVipExpiryUseCase) -> None:
        self._remind = remind

    async def run(self, now: datetime) -> dict[str, Any]:
        return dict((await self._remind.execute(now)).as_summary())


class FinalizeSeasonsTask:
    """F16.10, US-HG-05 — Chốt mùa thi đua đã kết thúc và trao thưởng; tự tạo mùa kế tiếp."""

    def __init__(self, finalize: FinalizeSeasonsUseCase) -> None:
        self._finalize = finalize

    async def run(self, now: datetime) -> dict[str, Any]:
        return dict((await self._finalize.execute(now)).as_summary())


class EvaluateAchievementsTask:
    """F16.11 — Quét mở khóa huy hiệu cho người có hoạt động trong ngày."""

    def __init__(self, evaluate: EvaluateAchievementsUseCase) -> None:
        self._evaluate = evaluate

    async def run(self, now: datetime) -> dict[str, Any]:
        return dict((await self._evaluate.execute(now)).as_summary())


class PurgeMinigameRoundsTask:
    """F16.01, F15.03 — Dọn lượt mini-game đã phát quá 7 ngày."""

    def __init__(self, purge: PurgeMinigameRoundsUseCase) -> None:
        self._purge = purge

    async def run(self, now: datetime) -> dict[str, Any]:
        return {"rounds": await self._purge.execute(now)}


def default_job_definitions(settings: Settings) -> list[JobDefinition]:
    """Danh sách tác vụ mặc định; chu kỳ lấy từ Settings (dọn ảnh 60 phút, FSRS 7 ngày, nhắc ôn 15 phút)
    và hằng số (nhắc VIP sắp hết hạn 60 phút, chốt mùa 15 phút, quét huy hiệu 60 phút)."""
    return [
        JobDefinition(CLEANUP_QUICK_UPLOADS, settings.cleanup_interval_minutes * 60),
        JobDefinition(CLEANUP_SESSIONS, SESSIONS_INTERVAL_SECONDS),
        JobDefinition(CLEANUP_ORPHAN_FILES, ORPHAN_FILES_INTERVAL_SECONDS),
        JobDefinition(OPTIMIZE_FSRS, settings.fsrs_optimize_interval_days * 86400),
        JobDefinition(SEND_REMINDERS, settings.reminder_scan_minutes * 60),
        JobDefinition(REMIND_VIP_EXPIRY, VIP_REMINDER_INTERVAL_SECONDS),
        JobDefinition(FINALIZE_SEASONS, FINALIZE_SEASONS_INTERVAL_SECONDS),
        JobDefinition(EVALUATE_ACHIEVEMENTS, EVALUATE_ACHIEVEMENTS_INTERVAL_SECONDS),
        JobDefinition(PURGE_MINIGAME_ROUNDS, PURGE_MINIGAME_ROUNDS_INTERVAL_SECONDS),
    ]


def build_job_tasks(
    session_factory: async_sessionmaker[AsyncSession], storage: FileStorage, clock: Clock, settings: Settings
) -> dict[str, JobTask]:
    def library_uow() -> LibraryUnitOfWork:
        return SqlLibraryUnitOfWork(session_factory)

    def auth_uow() -> AuthUnitOfWork:
        return SqlAuthUnitOfWork(session_factory)

    def reader_uow() -> ReaderUnitOfWork:
        return SqlReaderUnitOfWork(session_factory)

    def imaging_uow() -> ImagingUnitOfWork:
        return SqlImagingUnitOfWork(session_factory)

    def notifications_uow() -> NotificationsUnitOfWork:
        return SqlNotificationsUnitOfWork(session_factory)

    dictionary = DictionaryTermAdapter(session_factory)
    pages = LibraryPageAccess(library_uow, clock)

    def vocab_source(session: AsyncSession) -> VocabCardSource:
        return SqlVocabCardSource(session, dictionary, pages)

    def review_uow() -> ReviewUnitOfWork:
        return SqlReviewUnitOfWork(session_factory, vocab_source)

    def rewards_uow() -> RewardsUnitOfWork:
        return SqlRewardsUnitOfWork(session_factory)

    def gamification_uow() -> GamificationUnitOfWork:
        return SqlGamificationUnitOfWork(session_factory)

    notices = build_notice_sender(session_factory, clock)

    return {
        CLEANUP_QUICK_UPLOADS: CleanupQuickUploadsTask(PurgeExpiredQuickUploadsUseCase(library_uow, storage)),
        CLEANUP_SESSIONS: CleanupSessionsTask(
            PurgeExpiredSessionsUseCase(auth_uow), PurgeExpiredGuestSessionsUseCase(reader_uow)
        ),
        CLEANUP_ORPHAN_FILES: CleanupOrphanFilesTask(PurgeOrphanResultFilesUseCase(imaging_uow, storage)),
        OPTIMIZE_FSRS: OptimizeFsrsTask(
            OptimizeFsrsParametersUseCase(
                review_uow,
                FsrsLibraryOptimizer(),
                OptimizeConfig(
                    settings.fsrs_optimize_min_reviews,
                    settings.fsrs_optimize_interval_days,
                    settings.fsrs_optimize_max_users_per_run,
                ),
            )
        ),
        SEND_REMINDERS: SendRemindersTask(
            SendDueRemindersUseCase(
                notifications_uow,
                SqlDueCardCounter(session_factory),
                FileOutboxEmailSender(settings.storage_dir / "outbox"),
                ReminderConfig(settings.reminder_grace_hours),
            )
        ),
        REMIND_VIP_EXPIRY: RemindVipExpiryTask(
            RemindVipExpiryUseCase(
                rewards_uow, build_reward_notifier(session_factory, settings.storage_dir / "outbox", clock)
            )
        ),
        FINALIZE_SEASONS: FinalizeSeasonsTask(FinalizeSeasonsUseCase(gamification_uow, notices)),
        EVALUATE_ACHIEVEMENTS: EvaluateAchievementsTask(
            EvaluateAchievementsUseCase(gamification_uow, notices)
        ),
        PURGE_MINIGAME_ROUNDS: PurgeMinigameRoundsTask(PurgeMinigameRoundsUseCase(gamification_uow)),
    }


def build_job_runner(
    session_factory: async_sessionmaker[AsyncSession],
    storage: FileStorage,
    clock: Clock,
    settings: Settings,
) -> JobRunner:
    """Lắp `JobRunner` cho worker: `await runner.run_due_jobs(clock.now(), worker_id)`."""

    def jobs_uow() -> JobsUnitOfWork:
        return SqlJobsUnitOfWork(session_factory)

    return JobRunner(
        RunDueJobsUseCase(
            jobs_uow,
            clock,
            default_job_definitions(settings),
            build_job_tasks(session_factory, storage, clock, settings),
        )
    )
