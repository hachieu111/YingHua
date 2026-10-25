from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.security import TokenService
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.entities import Role
from app.modules.auth.domain.errors import AccountLockedError, SessionExpiredError


class AuthenticateUseCase:
    """F01.09 — Xác thực mã truy cập: chữ ký, hạn, phiên chưa bị thu hồi, tài khoản không bị khóa."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock, tokens: TokenService) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._tokens = tokens

    async def execute(self, access_token: str) -> Identity:
        claims = self._tokens.decode_access_token(access_token)
        async with self._uow_factory() as uow:
            user = await uow.users.get(claims.user_id)
            if user is None or not await uow.sessions.is_family_active(claims.session_id, self._clock.now()):
                raise SessionExpiredError("Phiên đăng nhập không còn hiệu lực")
            if user.is_locked:
                raise AccountLockedError()
        # Vai trò lấy từ CSDL (không tin vai trò trong token) nên đổi vai trò có hiệu lực ngay.
        return Identity(user_id=user.id, role=Role(user.role), session_id=claims.session_id)
