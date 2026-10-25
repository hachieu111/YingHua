"""Quy tắc thuần của M15."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.errors import DomainError
from app.modules.jobs.domain.entities import MAX_ERROR_CHARS, ScheduledJob


def next_run_at(job: ScheduledJob) -> datetime | None:
    """Thời điểm sớm nhất tác vụ chạy lại; None nếu đã tắt hoặc chưa từng chạy (đến hạn ngay)."""
    if not job.enabled or job.last_started_at is None:
        return None
    return job.last_started_at + timedelta(seconds=job.interval_seconds)


def describe_failure(exc: Exception) -> str:
    """Lý do lỗi lưu vào nhật ký chạy: thông điệp nghiệp vụ nếu có, ngược lại chỉ tên lỗi (không SQL,
    không đường dẫn máy chủ). Chi tiết đầy đủ nằm trong log."""
    text = exc.message if isinstance(exc, DomainError) else f"Lỗi nội bộ ({type(exc).__name__})"
    return text[:MAX_ERROR_CHARS]
