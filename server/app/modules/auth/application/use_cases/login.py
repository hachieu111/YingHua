from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import RateLimitedError
from app.core.rate_limit import FailureLimiter
from app.core.security import hash_password, password_needs_rehash, verify_password
from app.modules.auth.application.dto import AuthConfig, AuthResult
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.application.session_issuer import SessionIssuer
from app.modules.auth.domain.errors import AccountLockedError, InvalidCredentialsError
from app.modules.auth.domain.rules import normalize_email

log = logging.getLogger(__name__)

# Băm một mật khẩu giả khi email không tồn tại để thời gian phản hồi không lộ email có tồn tại hay không.
_DUMMY_HASH = hash_password("khong-ai-dung-mat-khau-nay")


class LoginUseCase:
    """F01.02 — Đăng nhập (US-KH-03). Sai email hay sai mật khẩu đều trả cùng một thông báo."""

    def __init__(
        self,
        uow_factory: Callable[[], AuthUnitOfWork],
        clock: Clock,
        issuer: SessionIssuer,
        limiter: FailureLimiter,
        config: AuthConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._issuer = issuer
        self._limiter = limiter
        self._config = config

    async def execute(self, email: str, password: str, user_agent: str | None, ip: str | None) -> AuthResult:
        email = normalize_email(email)
        email_key, ip_key = f"email:{email}", f"ip:{ip or '-'}"
        if self._limiter.is_blocked(
            email_key, self._config.login_max_attempts_per_email
        ) or self._limiter.is_blocked(ip_key, self._config.login_max_attempts_per_ip):
            raise RateLimitedError("Bạn đăng nhập sai quá nhiều lần, vui lòng thử lại sau ít phút")

        async with self._uow_factory() as uow:
            user = await uow.users.get_by_email(email)
            valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
            if user is None or not valid:
                self._limiter.record_failure(email_key)
                self._limiter.record_failure(ip_key)
                raise InvalidCredentialsError()
            # Chỉ báo khóa khi thông tin đăng nhập đã đúng (US-KH-03).
            if user.is_locked:
                raise AccountLockedError()
            self._limiter.reset(email_key)
            if password_needs_rehash(user.password_hash):
                user.password_hash = hash_password(password)
            user.last_login_at = self._clock.now()
            await uow.users.update(user)
            tokens = await self._issuer.open_session(uow, user, user_agent, ip)
            await uow.commit()
        log.info("Đăng nhập thành công user_id=%s", user.id)
        return AuthResult(user, tokens)
