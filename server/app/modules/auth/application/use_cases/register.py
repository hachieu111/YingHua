from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.clock import Clock
from app.core.security import hash_password
from app.core.welcome_gift import WelcomeGiftPort
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

logger = logging.getLogger(__name__)


class RegisterUseCase:
    """F01.01 — Đăng ký tài khoản (US-KH-02). Tài khoản mới luôn là Người học; tự đăng nhập sau khi tạo.

    Sau khi tài khoản đã lưu, tặng quà chào mừng 3 ngày VIP qua cổng của M17 (F17.03, US-NH-94 TC1, TC6).
    """

    def __init__(
        self,
        uow_factory: Callable[[], AuthUnitOfWork],
        clock: Clock,
        issuer: SessionIssuer,
        gift: WelcomeGiftPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._issuer = issuer
        self._gift = gift

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
        await self._grant_welcome_gift(user.id)
        return AuthResult(user, tokens)

    async def _grant_welcome_gift(self, user_id: int) -> None:
        """Quà chào mừng 3 ngày VIP (F17.03). Cấp lỗi thì đăng ký vẫn thành công, chỉ ghi cảnh báo."""
        try:
            await self._gift.grant_welcome(user_id)
        except Exception:
            logger.warning("Không tặng được quà chào mừng cho user_id=%s", user_id, exc_info=True)
