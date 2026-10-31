"""Thực thể của M15 Tác vụ nền — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

CLEANUP_QUICK_UPLOADS = "cleanup_quick_uploads"
CLEANUP_SESSIONS = "cleanup_sessions"
CLEANUP_ORPHAN_FILES = "cleanup_orphan_files"
OPTIMIZE_FSRS = "optimize_fsrs"
SEND_REMINDERS = "send_reminders"
REMIND_VIP_EXPIRY = "remind_vip_expiry"  # nhắc VIP sắp hết hạn (F17.03, US-HG-06)
FINALIZE_SEASONS = "finalize_seasons"  # chốt mùa thi đua và trao thưởng (F16.10, US-HG-05)
EVALUATE_ACHIEVEMENTS = "evaluate_achievements"  # quét mở khóa huy hiệu (F16.11)
PURGE_MINIGAME_ROUNDS = "purge_minigame_rounds"  # dọn lượt mini-game cũ (F16.01, F15.03)

# Khóa chống chạy chồng tự hết hạn: nếu worker chết giữa chừng, tác vụ chạy lại được sau chừng này.
JOB_LOCK_TTL = timedelta(minutes=10)
SESSIONS_INTERVAL_SECONDS = 6 * 3600
ORPHAN_FILES_INTERVAL_SECONDS = 24 * 3600
VIP_REMINDER_INTERVAL_SECONDS = 60 * 60
FINALIZE_SEASONS_INTERVAL_SECONDS = 15 * 60
EVALUATE_ACHIEVEMENTS_INTERVAL_SECONDS = 60 * 60
PURGE_MINIGAME_ROUNDS_INTERVAL_SECONDS = 24 * 3600
MAX_ERROR_CHARS = 1000


class JobStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobDefinition:
    """Tác vụ định kỳ cần có trong `scheduled_jobs` (F15.03)."""

    name: str
    interval_seconds: int


@dataclass(slots=True)
class ScheduledJob:
    name: str
    interval_seconds: int
    enabled: bool
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_status: JobStatus | None = None
    locked_until: datetime | None = None
    locked_by: str | None = None


@dataclass(slots=True)
class JobRun:
    id: int
    job_name: str
    started_at: datetime
    status: JobStatus
    finished_at: datetime | None = None
    summary: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    name: str
    run_id: int


@dataclass(frozen=True, slots=True)
class JobView:
    """Tác vụ kèm lần chạy gần nhất, để Quản trị viên theo dõi (F15.03)."""

    job: ScheduledJob
    last_run: JobRun | None
    next_run_at: datetime | None  # None: đến hạn ngay (chưa từng chạy) hoặc đã tắt
