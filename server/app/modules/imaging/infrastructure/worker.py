"""Lắp ghép `WorkerJobs` cho process worker (dùng chung CSDL và FileStorage với API)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.core.storage import FileStorage
from app.modules.imaging.application.dto import JobConfig
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.application.use_cases.claim_next_job import ClaimNextJobUseCase
from app.modules.imaging.application.use_cases.complete_job import CompleteJobUseCase
from app.modules.imaging.application.use_cases.fail_job import FailJobUseCase
from app.modules.imaging.application.use_cases.store_result_image import StoreResultImageUseCase
from app.modules.imaging.application.worker import WorkerJobs
from app.modules.imaging.infrastructure.uow import SqlImagingUnitOfWork


def job_config(settings: Settings) -> JobConfig:
    return JobConfig(
        max_attempts=settings.job_max_attempts, stale_after=timedelta(minutes=settings.job_stale_minutes)
    )


def build_worker_jobs(
    session_factory: async_sessionmaker[AsyncSession], storage: FileStorage, clock: Clock, settings: Settings
) -> WorkerJobs:
    def uow_factory() -> ImagingUnitOfWork:
        return SqlImagingUnitOfWork(session_factory)

    config = job_config(settings)
    return WorkerJobs(
        claim=ClaimNextJobUseCase(uow_factory, config),
        complete=CompleteJobUseCase(uow_factory, clock, storage),
        fail=FailJobUseCase(uow_factory, clock, config),
        store_image=StoreResultImageUseCase(uow_factory, clock, storage),
    )
