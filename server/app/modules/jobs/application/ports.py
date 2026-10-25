"""Giao diện (port) mà tầng hạ tầng của M15 phải hiện thực."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from app.modules.jobs.domain.entities import (
    ClaimedJob,
    JobDefinition,
    JobRun,
    JobStatus,
    ScheduledJob,
)


class JobRepository(Protocol):
    async def seed(self, definitions: Sequence[JobDefinition]) -> None:
        """Thêm tác vụ còn thiếu; tác vụ đã có giữ nguyên (idempotent, không ghi đè chu kỳ đã chỉnh)."""
        ...

    async def claim_due(self, now: datetime, worker_id: str, lock_until: datetime) -> list[ClaimedJob]:
        """Nguyên tử: chọn tác vụ đến hạn và không bị khóa (`FOR UPDATE SKIP LOCKED`), đặt khóa và
        `last_started_at`, mở dòng `job_runs` ở trạng thái `running`."""
        ...

    async def finish(
        self,
        claimed: ClaimedJob,
        status: JobStatus,
        now: datetime,
        summary: dict[str, Any] | None,
        error_message: str | None,
    ) -> None:
        """Đóng dòng `job_runs` và nhả khóa của tác vụ."""
        ...

    async def list_jobs(self) -> list[tuple[ScheduledJob, JobRun | None]]:
        """Mọi tác vụ kèm lần chạy gần nhất."""
        ...


class JobTask(Protocol):
    """Một việc định kỳ cụ thể (dọn dẹp...). Trả bản tóm tắt để ghi vào `job_runs.summary`."""

    async def run(self, now: datetime) -> dict[str, Any]: ...


class JobsUnitOfWork(Protocol):
    @property
    def jobs(self) -> JobRepository: ...

    async def __aenter__(self) -> JobsUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
