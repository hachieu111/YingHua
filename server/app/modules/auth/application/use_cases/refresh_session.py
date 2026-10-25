from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.clock import Clock
from app.core.security import hash_token
from app.modules.auth.application.dto import AuthResult
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.application.session_issuer import SessionIssuer
from app.modules.auth.domain.errors import AccountLockedError, SessionExpiredError

log = logging.getLogger(__name__)


class RefreshSessionUseCase:
    """F01.03 — Làm mới phiên (US-NH-01): xoay vòng mã làm mới, đọc lại vai trò và trạng thái khóa."""

    def __init__(
        self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock, issuer: SessionIssuer
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._issuer = issuer

    async def execute(self, refresh_token: str, user_agent: str | None, ip: str | None) -> AuthResult:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            session = await uow.sessions.get_by_token_hash(hash_token(refresh_token))
            if session is None:
                raise SessionExpiredError()
            if session.replaced_by_id is not None:
                # Mã đã được thay mà vẫn bị gửi lại: nghi bị đánh cắp, thu hồi cả phiên.
                log.warning(
                    "Phát hiện dùng lại mã làm mới đã xoay vòng, thu hồi phiên user_id=%s", session.user_id
                )
                await uow.sessions.revoke_family(session.family_id, now)
                await uow.commit()
                raise SessionExpiredError()
            if session.revoked_at is not None or session.expires_at <= now:
                raise SessionExpiredError()
            user = await uow.users.get(session.user_id)
            if user is None:
                raise SessionExpiredError()
            if user.is_locked:
                await uow.sessions.revoke_family(session.family_id, now)
                await uow.commit()
                raise AccountLockedError()
            tokens = await self._issuer.rotate(uow, user, session.family_id, session.id, user_agent, ip)
            await uow.commit()
        return AuthResult(user, tokens)
