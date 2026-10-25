from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.domain.errors import UserNotFoundError
from app.modules.auth.application.public import Identity, User


class EnsureTargetUserUseCase:
    """F13.07 — Xác nhận người gọi là quản trị viên và người dùng đích tồn tại."""

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity, target_user_id: int) -> User:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            user = await uow.users.get(target_user_id)
        if user is None:
            raise UserNotFoundError()
        return user
