from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.application.dto import AuditLogFilter, AuditLogItem, PersonRef
from app.modules.admin.infrastructure import foreign_tables as ft
from app.modules.admin.infrastructure.orm_models import AdminAuditLogModel as Log


class SqlAuditLogReader:
    """Đọc `admin_audit_logs` (F13.06): lọc theo người thực hiện, thao tác, đối tượng, khoảng thời gian."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self, filters: AuditLogFilter, offset: int, limit: int
    ) -> tuple[list[AuditLogItem], int]:
        conditions: list[Any] = []
        if filters.admin_id is not None:
            conditions.append(Log.admin_id == filters.admin_id)
        if filters.action:
            conditions.append(Log.action == filters.action)
        if filters.target_type:
            conditions.append(Log.target_type == filters.target_type)
        if filters.since is not None:
            conditions.append(Log.created_at >= filters.since)
        if filters.until is not None:
            conditions.append(Log.created_at < filters.until)
        total = await self._session.scalar(select(func.count()).select_from(Log).where(*conditions))
        rows = await self._session.execute(
            select(Log, ft.users.c.display_name, ft.users.c.email)
            .outerjoin(ft.users, ft.users.c.id == Log.admin_id)
            .where(*conditions)
            .order_by(Log.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = [
            AuditLogItem(
                id=log.id,
                admin=None if log.admin_id is None else PersonRef(log.admin_id, name or "", email or ""),
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                details=log.details,
                created_at=log.created_at,
            )
            for log, name, email in rows.all()
        ]
        return items, int(total or 0)
