from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.clock import Clock
from app.modules.jobs.application.ports import JobsUnitOfWork, JobTask
from app.modules.jobs.domain.entities import JOB_LOCK_TTL, JobDefinition, JobStatus
from app.modules.jobs.domain.rules import describe_failure

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class JobRunReport:
    name: str
    run_id: int
    status: JobStatus
    summary: dict[str, Any] | None
    error_message: str | None


class RunDueJobsUseCase:
    """F15.03, F15.01, F15.02 — Chạy các tác vụ định kỳ đến hạn (US-HG-01, TC5).

    Mỗi tác vụ: lấy khóa nguyên tử (hai worker không chạy chồng), chạy trong khối bắt lỗi riêng, ghi
    `job_runs` (running → ok/failed, kèm tóm tắt hoặc lý do lỗi), rồi nhả khóa. Lỗi của một tác vụ không
    chặn tác vụ khác cũng như lần chạy kế tiếp.
    """

    def __init__(
        self,
        uow_factory: Callable[[], JobsUnitOfWork],
        clock: Clock,
        definitions: Sequence[JobDefinition],
        tasks: Mapping[str, JobTask],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._definitions = definitions
        self._tasks = tasks

    async def execute(self, now: datetime, worker_id: str) -> list[JobRunReport]:
        async with self._uow_factory() as uow:
            await uow.jobs.seed(self._definitions)
            claimed = await uow.jobs.claim_due(now, worker_id, now + JOB_LOCK_TTL)
            await uow.commit()
        reports: list[JobRunReport] = []
        for job in claimed:
            status, summary, error = await self._run_one(job.name, now)
            async with self._uow_factory() as uow:
                await uow.jobs.finish(job, status, self._clock.now(), summary, error)
                await uow.commit()
            reports.append(JobRunReport(job.name, job.run_id, status, summary, error))
        return reports

    async def _run_one(self, name: str, now: datetime) -> tuple[JobStatus, dict[str, Any] | None, str | None]:
        task = self._tasks.get(name)
        if task is None:
            return JobStatus.FAILED, None, "Tác vụ chưa được đăng ký trong worker"
        try:
            summary = await task.run(now)
        except Exception as exc:  # cô lập lỗi từng tác vụ; chi tiết ghi log, lý do rút gọn ghi nhật ký chạy
            logger.exception("Tác vụ nền %s lỗi", name)
            return JobStatus.FAILED, None, describe_failure(exc)
        logger.info("Tác vụ nền %s xong: %s", name, summary)
        return JobStatus.OK, summary, None
