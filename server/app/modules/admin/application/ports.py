from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.modules.admin.application.dto import UserActivity
from app.modules.auth.application.public import Identity, SessionRepository, UserRepository


class AuditLogRepository(Protocol):
    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None:
        """Bản ghi chỉ thêm (F13.06): không có thao tác sửa hay xóa."""
        ...


class UserActivitySource(Protocol):
    """Gom số liệu của một người dùng từ các module sở hữu dữ liệu (M03, M07, M08)."""

    async def collect(self, actor: Identity, user_id: int) -> UserActivity: ...


class AdminUnitOfWork(Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    async def __aenter__(self) -> AdminUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
