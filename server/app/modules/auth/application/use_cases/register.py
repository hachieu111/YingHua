from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.security import hash_password
from app.modules.auth.application.dto import AuthResult
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.application.session_issuer import SessionIssuer
from app.modules.auth.domain.entities import NewUser
from app.modules.auth.domain.errors import EmailAlreadyUsedError
from app.modules.auth.domain.rules import (
    clean_display_name,
    default_display_name,
    normalize_email,
    validate_password,
)


class RegisterUseCase:
    """F01.01 — Đăng ký tài khoản (US-KH-02). Tài khoản mới luôn là Người học; tự đăng nhập sau khi tạo."""

    def __init__(
        self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock, issuer: SessionIssuer
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._issuer = issuer

    async def execute(
        self, email: str, password: str, display_name: str | None, user_agent: str | None, ip: str | None
    ) -> AuthResult:
        email = normalize_email(email)
        validate_password(password)
        name = (
            clean_display_name(display_name)
            if display_name and display_name.strip()
            else default_display_name(email)
        )
        password_hash = hash_password(password)
        async with self._uow_factory() as uow:
            if await uow.users.get_by_email(email) is not None:
                raise EmailAlreadyUsedError()
            user = await uow.users.add(NewUser(email, password_hash, name, self._clock.now()))
            tokens = await self._issuer.open_session(uow, user, user_agent, ip)
            await uow.commit()
        return AuthResult(user, tokens)
