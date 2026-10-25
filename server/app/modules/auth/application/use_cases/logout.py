from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork


class LogoutUseCase:
    """F01.04 — Đăng xuất thiết bị hiện tại (US-NH-02): chỉ thu hồi phiên của thiết bị này."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> None:
        async with self._uow_factory() as uow:
            await uow.sessions.revoke_family(identity.session_id, self._clock.now())
            await uow.commit()
