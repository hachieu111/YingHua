from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.auth.application.public import Identity, User

MAX_PAGE_SIZE = 100


class ListUsersUseCase:
    """F13.01 — Xem và tìm người dùng theo email (US-QT-01). Không trả mật khẩu hay dữ liệu học tập."""

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, actor: Identity, query: str | None, page: int, size: int
    ) -> tuple[list[User], int]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        size = max(1, min(size, MAX_PAGE_SIZE))
        page = max(1, page)
        async with self._uow_factory() as uow:
            return await uow.users.search(query, (page - 1) * size, size)
