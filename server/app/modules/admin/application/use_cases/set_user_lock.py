from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import NotFoundError, PermissionDeniedError
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.domain.errors import SelfLockError
from app.modules.auth.application.public import Identity, User, UserStatus


class SetUserLockUseCase:
    """F13.03 — Khóa / mở khóa tài khoản (US-QT-03). Khóa thu hồi mọi phiên; mở khóa giữ nguyên dữ liệu."""

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, actor: Identity, target_id: int, lock: bool, reason: str | None) -> User:
        if not actor.is_admin:
            raise PermissionDeniedError()
        if lock and actor.user_id == target_id:
            raise SelfLockError()
        now = self._clock.now()
        async with self._uow_factory() as uow:
            target = await uow.users.get(target_id)
            if target is None:
                raise NotFoundError("Không tìm thấy người dùng")
            reason = (reason or "").strip()[:500] or None
            if lock:
                target.status = UserStatus.LOCKED
                target.locked_reason = reason
                target.locked_at = now
                await uow.sessions.revoke_user_sessions(target_id, now)
            else:
                target.status = UserStatus.ACTIVE
                target.locked_reason = None
                target.locked_at = None
            await uow.users.update(target)
            await uow.audit.add(
                actor.user_id,
                "user.locked" if lock else "user.unlocked",
                "user",
                target_id,
                {"reason": reason} if lock else {},
                now,
            )
            await uow.commit()
        return target
