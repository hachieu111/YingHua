from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.domain.entities import (
    ClaimedJob,
    JobDefinition,
    JobRun,
    JobStatus,
    ScheduledJob,
)
from app.modules.jobs.infrastructure.orm_models import JobRunModel, ScheduledJobModel


def _job(m: ScheduledJobModel) -> ScheduledJob:
    return ScheduledJob(
        name=m.name,
        interval_seconds=m.interval_seconds,
        enabled=m.enabled,
        last_started_at=m.last_started_at,
        last_finished_at=m.last_finished_at,
        last_status=JobStatus(m.last_status) if m.last_status else None,
        locked_until=m.locked_until,
        locked_by=m.locked_by,
    )


def _run(m: JobRunModel) -> JobRun:
    return JobRun(
        id=m.id,
        job_name=m.job_name,
        started_at=m.started_at,
        status=JobStatus(m.status),
        finished_at=m.finished_at,
        summary=m.summary,
        error_message=m.error_message,
    )


class SqlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def seed(self, definitions: Sequence[JobDefinition]) -> None:
        if not definitions:
            return
        stmt = insert(ScheduledJobModel).values(
            [{"name": d.name, "interval_seconds": d.interval_seconds, "enabled": True} for d in definitions]
        )
        await self._session.execute(stmt.on_conflict_do_nothing(index_elements=[ScheduledJobModel.name]))

    async def claim_due(self, now: datetime, worker_id: str, lock_until: datetime) -> list[ClaimedJob]:
        next_due = ScheduledJobModel.last_started_at + func.make_interval(
            0, 0, 0, 0, 0, 0, ScheduledJobModel.interval_seconds
        )
        due_names = (
            select(ScheduledJobModel.name)
            .where(
                ScheduledJobModel.enabled.is_(True),
                or_(ScheduledJobModel.last_started_at.is_(None), next_due <= now),
                or_(ScheduledJobModel.locked_until.is_(None), ScheduledJobModel.locked_until <= now),
            )
            .order_by(ScheduledJobModel.name)
            .with_for_update(skip_locked=True)
        )
        rows = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.name.in_(due_names))
            .values(locked_until=lock_until, locked_by=worker_id, last_started_at=now)
            .returning(ScheduledJobModel.name)
        )
        claimed: list[ClaimedJob] = []
        for (name,) in sorted(rows.all()):
            run = JobRunModel(job_name=name, started_at=now, status=JobStatus.RUNNING.value)
            self._session.add(run)
            await self._session.flush()
            claimed.append(ClaimedJob(name=name, run_id=run.id))
        return claimed

    async def finish(
        self,
        claimed: ClaimedJob,
        status: JobStatus,
        now: datetime,
        summary: dict[str, Any] | None,
        error_message: str | None,
    ) -> None:
        await self._session.execute(
            update(JobRunModel)
            .where(JobRunModel.id == claimed.run_id)
            .values(status=status.value, finished_at=now, summary=summary, error_message=error_message)
        )
        await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.name == claimed.name)
            .values(last_finished_at=now, last_status=status.value, locked_until=None, locked_by=None)
        )

    async def list_jobs(self) -> list[tuple[ScheduledJob, JobRun | None]]:
        jobs = (
            (await self._session.execute(select(ScheduledJobModel).order_by(ScheduledJobModel.name)))
            .scalars()
            .all()
        )
        latest = (
            (
                await self._session.execute(
                    select(JobRunModel)
                    .distinct(JobRunModel.job_name)
                    .order_by(JobRunModel.job_name, JobRunModel.started_at.desc(), JobRunModel.id.desc())
                )
            )
            .scalars()
            .all()
        )
        last_by_job = {r.job_name: _run(r) for r in latest}
        return [(_job(j), last_by_job.get(j.name)) for j in jobs]
