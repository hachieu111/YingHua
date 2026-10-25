from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.infrastructure.orm_models import AdminAuditLogModel


class SqlAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None:
        self._session.add(
            AdminAuditLogModel(
                admin_id=admin_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=details,
                created_at=at,
            )
        )
        await self._session.flush()
