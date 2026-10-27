from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.stats.infrastructure.repositories import SqlActivityRepository


class SqlStatsUnitOfWork(SqlAlchemyUnitOfWork):
    activity: SqlActivityRepository

    def _init_repositories(self) -> None:
        self.activity = SqlActivityRepository(self.session)
