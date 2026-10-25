from __future__ import annotations

from collections.abc import Callable, Sequence

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.jobs.application.ports import JobsUnitOfWork
from app.modules.jobs.domain.entities import JobDefinition, JobView
from app.modules.jobs.domain.rules import next_run_at


class ListJobsUseCase:
    """F15.03 — Quản trị viên xem trạng thái các tác vụ định kỳ và lần chạy gần nhất (US-HG-01)."""

    def __init__(
        self, uow_factory: Callable[[], JobsUnitOfWork], definitions: Sequence[JobDefinition]
    ) -> None:
        self._uow_factory = uow_factory
        self._definitions = definitions

    async def execute(self, admin: Identity) -> list[JobView]:
        if not admin.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            await uow.jobs.seed(self._definitions)  # idempotent: để danh sách luôn đủ tác vụ mặc định
            await uow.commit()
            rows = await uow.jobs.list_jobs()
        return [JobView(job=job, last_run=run, next_run_at=next_run_at(job)) for job, run in rows]
