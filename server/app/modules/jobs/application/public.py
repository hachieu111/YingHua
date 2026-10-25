"""Bề mặt công khai của M15 cho worker: gọi `run_due_jobs` định kỳ (ví dụ mỗi 30–60 giây)."""

from __future__ import annotations

from datetime import datetime

from app.modules.jobs.application.use_cases.run_due_jobs import JobRunReport, RunDueJobsUseCase


class JobRunner:
    """Điều phối tác vụ định kỳ cho worker."""

    def __init__(self, use_case: RunDueJobsUseCase) -> None:
        self._use_case = use_case

    async def run_due_jobs(self, now: datetime, worker_id: str) -> list[JobRunReport]:
        """Chạy mọi tác vụ đến hạn và chưa bị worker khác khóa; trả báo cáo từng tác vụ đã chạy."""
        return await self._use_case.execute(now, worker_id)


__all__ = ["JobRunReport", "JobRunner"]
