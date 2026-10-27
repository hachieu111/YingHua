from __future__ import annotations

from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.modules.auth.api.public import Identity, require_admin
from app.modules.jobs.api.schemas import JobListResponse, JobResponse
from app.modules.jobs.application.ports import JobsUnitOfWork
from app.modules.jobs.application.use_cases.list_jobs import ListJobsUseCase
from app.modules.jobs.infrastructure.tasks import default_job_definitions
from app.modules.jobs.infrastructure.uow import SqlJobsUnitOfWork

router = APIRouter(prefix="/admin/jobs", tags=["M15 Tác vụ nền"])


@router.get("", response_model=JobListResponse, summary="Trạng thái các tác vụ định kỳ (F15.03)")
async def list_jobs(
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> JobListResponse:
    def uow_factory() -> JobsUnitOfWork:
        return SqlJobsUnitOfWork(container.session_factory)

    definitions = default_job_definitions(container.settings)
    views = await ListJobsUseCase(uow_factory, definitions).execute(admin)
    return JobListResponse(items=[JobResponse.from_view(v) for v in views])
