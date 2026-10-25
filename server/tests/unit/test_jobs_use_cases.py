"""M15 — điều phối tác vụ định kỳ với repository giả: F15.03."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity, Role
from app.modules.jobs.application.use_cases.list_jobs import ListJobsUseCase
from app.modules.jobs.application.use_cases.run_due_jobs import RunDueJobsUseCase
from app.modules.jobs.domain.entities import (
    ClaimedJob,
    JobDefinition,
    JobRun,
    JobStatus,
    ScheduledJob,
)
from app.modules.jobs.domain.rules import describe_failure, next_run_at
from tests.conftest import FixedClock

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
DEFS = [JobDefinition("a", 3600), JobDefinition("b", 3600), JobDefinition("c", 3600)]


class FakeJobs:
    def __init__(self) -> None:
        self.jobs: dict[str, ScheduledJob] = {}
        self.runs: dict[int, JobRun] = {}

    async def seed(self, definitions: Sequence[JobDefinition]) -> None:
        for d in definitions:
            self.jobs.setdefault(d.name, ScheduledJob(d.name, d.interval_seconds, True))

    async def claim_due(self, now: datetime, worker_id: str, lock_until: datetime) -> list[ClaimedJob]:
        claimed: list[ClaimedJob] = []
        for job in sorted(self.jobs.values(), key=lambda j: j.name):
            due = (
                job.last_started_at is None
                or job.last_started_at + timedelta(seconds=job.interval_seconds) <= now
            )
            if job.enabled and due and (job.locked_until is None or job.locked_until <= now):
                job.last_started_at, job.locked_until, job.locked_by = now, lock_until, worker_id
                run = JobRun(len(self.runs) + 1, job.name, now, JobStatus.RUNNING)
                self.runs[run.id] = run
                claimed.append(ClaimedJob(job.name, run.id))
        return claimed

    async def finish(
        self, claimed: ClaimedJob, status: JobStatus, now: datetime, summary: Any, error: str | None
    ) -> None:
        run = self.runs[claimed.run_id]
        run.status, run.finished_at, run.summary, run.error_message = status, now, summary, error
        job = self.jobs[claimed.name]
        job.last_status, job.last_finished_at, job.locked_until, job.locked_by = status, now, None, None

    async def list_jobs(self) -> list[tuple[ScheduledJob, JobRun | None]]:
        return [(j, None) for j in self.jobs.values()]


class FakeUow:
    def __init__(self, jobs: FakeJobs) -> None:
        self.jobs = jobs

    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class OkTask:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self, now: datetime) -> dict[str, Any]:
        self.calls += 1
        return {"removed": 3}


class FailingTask:
    async def run(self, now: datetime) -> dict[str, Any]:
        raise RuntimeError("SELECT secret FROM users")


def _runner(jobs: FakeJobs, tasks: dict[str, Any]) -> RunDueJobsUseCase:
    return RunDueJobsUseCase(lambda: FakeUow(jobs), FixedClock(NOW), DEFS, tasks)  # type: ignore[arg-type,return-value]


async def test_failing_job_is_isolated_logged_and_does_not_block_others() -> None:
    """US-HG-01 TC5: lỗi của một tác vụ không ảnh hưởng tác vụ khác; lý do lỗi không lộ chi tiết nội bộ."""
    jobs, ok = FakeJobs(), OkTask()
    reports = await _runner(jobs, {"a": ok, "b": FailingTask()}).execute(NOW, "w1")
    by_name = {r.name: r for r in reports}
    assert by_name["a"].status is JobStatus.OK and by_name["a"].summary == {"removed": 3}
    assert by_name["b"].status is JobStatus.FAILED and "SELECT" not in (by_name["b"].error_message or "")
    assert by_name["c"].status is JobStatus.FAILED  # chưa đăng ký trong worker
    assert all(j.locked_by is None for j in jobs.jobs.values())  # khóa đã nhả kể cả khi lỗi
    assert jobs.runs[by_name["b"].run_id].status is JobStatus.FAILED


async def test_job_runs_only_when_due_and_failure_does_not_block_next_run() -> None:
    jobs, ok = FakeJobs(), OkTask()
    runner = _runner(jobs, {"a": ok, "b": ok, "c": ok})
    assert len(await runner.execute(NOW, "w1")) == 3
    assert await runner.execute(NOW + timedelta(minutes=30), "w1") == []  # chưa tới chu kỳ
    assert len(await runner.execute(NOW + timedelta(hours=1), "w1")) == 3
    assert ok.calls == 6


async def test_locked_job_is_not_run_by_second_worker() -> None:
    """Khóa chống chạy chồng: tác vụ đang bị khóa (chưa hết hạn) không được nhận lần nữa."""
    jobs = FakeJobs()
    await jobs.seed(DEFS)
    jobs.jobs["a"].locked_until = NOW + timedelta(minutes=5)
    reports = await _runner(jobs, {"a": OkTask(), "b": OkTask(), "c": OkTask()}).execute(NOW, "w2")
    assert sorted(r.name for r in reports) == ["b", "c"]


async def test_list_jobs_is_admin_only_and_next_run_follows_interval() -> None:
    """US-HG-01: chỉ quản trị viên xem; chưa chạy → đến hạn ngay."""
    jobs = FakeJobs()
    use_case = ListJobsUseCase(lambda: FakeUow(jobs), DEFS)  # type: ignore[arg-type,return-value]
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(Identity(1, Role.USER, "s"))
    views = await use_case.execute(Identity(1, Role.ADMIN, "s"))
    assert [v.job.name for v in views] == ["a", "b", "c"] and all(v.next_run_at is None for v in views)
    job = ScheduledJob("a", 600, True, last_started_at=NOW)
    assert next_run_at(job) == NOW + timedelta(minutes=10)
    job.enabled = False
    assert next_run_at(job) is None


def test_describe_failure_hides_internal_details() -> None:
    assert describe_failure(RuntimeError("password=abc")) == "Lỗi nội bộ (RuntimeError)"
