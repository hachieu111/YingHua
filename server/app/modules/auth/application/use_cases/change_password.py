from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import NotFoundError
from app.core.security import hash_password, verify_password
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.errors import SamePasswordError, WrongCurrentPasswordError
from app.modules.auth.domain.rules import validate_password


class ChangePasswordUseCase:
    """F01.08 — Đổi mật khẩu (US-NH-05). Giữ phiên hiện tại, thu hồi các phiên khác."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, current_password: str, new_password: str) -> None:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(identity.user_id)
            if user is None:
                raise NotFoundError("Không tìm thấy tài khoản")
            if not verify_password(current_password, user.password_hash):
                raise WrongCurrentPasswordError()
            validate_password(new_password)
            if new_password == current_password:
                raise SamePasswordError()
            user.password_hash = hash_password(new_password)
            user.password_changed_at = now
            await uow.users.update(user)
            await uow.sessions.revoke_user_sessions(user.id, now, except_family=identity.session_id)
            await uow.commit()
