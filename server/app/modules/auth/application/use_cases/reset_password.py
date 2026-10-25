from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.security import hash_password, hash_token
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.errors import ResetLinkInvalidError
from app.modules.auth.domain.rules import validate_password


class ResetPasswordUseCase:
    """F01.06 (bước 2) — Đặt mật khẩu mới bằng mã trong liên kết; thu hồi mọi phiên cũ."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, token: str, new_password: str) -> None:
        validate_password(new_password)
        now = self._clock.now()
        password_hash = hash_password(new_password)
        async with self._uow_factory() as uow:
            reset = await uow.resets.get_by_token_hash(hash_token(token))
            if reset is None or reset.used_at is not None or reset.expires_at <= now:
                raise ResetLinkInvalidError()
            user = await uow.users.get(reset.user_id)
            if user is None or user.is_locked:
                raise ResetLinkInvalidError()
            user.password_hash = password_hash
            user.password_changed_at = now
            await uow.users.update(user)
            await uow.resets.mark_used(reset.id, now)
            await uow.sessions.revoke_user_sessions(user.id, now)
            await uow.commit()
