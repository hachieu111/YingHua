from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.jobs.infrastructure.repositories import SqlJobRepository


class SqlJobsUnitOfWork(SqlAlchemyUnitOfWork):
    jobs: SqlJobRepository

    def _init_repositories(self) -> None:
        self.jobs = SqlJobRepository(self.session)
