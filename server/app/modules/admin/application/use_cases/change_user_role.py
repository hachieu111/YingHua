from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import NotFoundError, PermissionDeniedError
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.domain.errors import SelfDemoteError
from app.modules.auth.application.public import Identity, Role, User


class ChangeUserRoleUseCase:
    """F13.02 — Đổi vai trò người dùng (US-QT-02). Không tự hạ quyền chính mình; ghi nhật ký (F13.06)."""

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, actor: Identity, target_id: int, new_role: Role) -> User:
        if not actor.is_admin:
            raise PermissionDeniedError()
        if actor.user_id == target_id and new_role is not Role.ADMIN:
            raise SelfDemoteError()
        async with self._uow_factory() as uow:
            target = await uow.users.get(target_id)
            if target is None:
                raise NotFoundError("Không tìm thấy người dùng")
            previous = target.role
            if previous is not new_role:
                target.role = new_role
                await uow.users.update(target)
                await uow.audit.add(
                    actor.user_id,
                    "user.role_changed",
                    "user",
                    target_id,
                    {"from": previous.value, "to": new_role.value},
                    self._clock.now(),
                )
            await uow.commit()
        return target
