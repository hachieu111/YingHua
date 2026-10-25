from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork


class LogoutAllUseCase:
    """F01.05 — Đăng xuất mọi thiết bị (US-NH-03). Nguyên tử: trong một giao dịch."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> int:
        async with self._uow_factory() as uow:
            revoked = await uow.sessions.revoke_user_sessions(identity.user_id, self._clock.now())
            await uow.commit()
        return revoked
