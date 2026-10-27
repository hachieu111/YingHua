from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import RemovalItem
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.auth.application.public import Identity


class ListContentRemovalsUseCase:
    """F13.04 — Danh sách ảnh/trang đã gỡ kèm lý do và người gỡ (US-QT-12 TC4)."""

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity, page: int, size: int) -> tuple[list[RemovalItem], int]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            return await uow.moderation.list_removals((page - 1) * size, size)
