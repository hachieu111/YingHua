from __future__ import annotations

import logging
from collections.abc import Callable
from urllib.parse import quote

from app.core.clock import Clock
from app.core.security import hash_token, new_opaque_token
from app.modules.auth.application.dto import AuthConfig
from app.modules.auth.application.ports import AuthUnitOfWork, EmailSender
from app.modules.auth.domain.rules import normalize_email

log = logging.getLogger(__name__)


class RequestPasswordResetUseCase:
    """F01.06 (bước 1) — Gửi liên kết đặt lại mật khẩu (US-KH-06). Không lộ email có tồn tại hay không."""

    def __init__(
        self,
        uow_factory: Callable[[], AuthUnitOfWork],
        clock: Clock,
        email_sender: EmailSender,
        config: AuthConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._email_sender = email_sender
        self._config = config

    async def execute(self, email: str) -> None:
        email = normalize_email(email)
        link: str | None = None
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_email(email)
            if user is not None and not user.is_locked:
                token = new_opaque_token()
                now = self._clock.now()
                await uow.resets.add(user.id, hash_token(token), now + self._config.reset_ttl, now)
                await uow.commit()
                link = f"{self._config.frontend_url.rstrip('/')}/?reset_token={quote(token)}"
        if link is not None:
            try:
                await self._email_sender.send_password_reset(email, link)
            except Exception:
                # Người dùng vẫn nhận thông báo chung và có thể yêu cầu lại.
                log.exception("Không gửi được email đặt lại mật khẩu")
