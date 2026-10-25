from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.modules.jobs.domain.entities import JobRun, JobView


class JobRunResponse(BaseModel):
    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    summary: dict[str, Any] | None
    error_message: str | None

    @classmethod
    def from_entity(cls, r: JobRun) -> JobRunResponse:
        return cls(
            id=r.id,
            status=r.status.value,
            started_at=r.started_at,
            finished_at=r.finished_at,
            summary=r.summary,
            error_message=r.error_message,
        )


class JobResponse(BaseModel):
    name: str
    interval_seconds: int
    enabled: bool
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_status: str | None
    next_run_at: datetime | None
    locked_until: datetime | None
    locked_by: str | None
    last_run: JobRunResponse | None

    @classmethod
    def from_view(cls, v: JobView) -> JobResponse:
        j = v.job
        return cls(
            name=j.name,
            interval_seconds=j.interval_seconds,
            enabled=j.enabled,
            last_started_at=j.last_started_at,
            last_finished_at=j.last_finished_at,
            last_status=j.last_status.value if j.last_status else None,
            next_run_at=v.next_run_at,
            locked_until=j.locked_until,
            locked_by=j.locked_by,
            last_run=JobRunResponse.from_entity(v.last_run) if v.last_run else None,
        )


class JobListResponse(BaseModel):
    items: list[JobResponse]
