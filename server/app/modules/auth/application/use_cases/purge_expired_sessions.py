from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.auth.application.ports import AuthUnitOfWork

REVOKED_RETENTION = timedelta(days=7)  # giữ vết phiên đã thu hồi một thời gian để điều tra


@dataclass(frozen=True, slots=True)
class SessionPurgeReport:
    refresh_tokens: int
    reset_tokens: int


class PurgeExpiredSessionsUseCase:
    """F15.02 — Xóa phiên đăng nhập hết hạn (mã làm mới hết hạn hoặc đã thu hồi quá 7 ngày) và liên kết
    đặt lại mật khẩu hết hạn (US-HG-01). Phiên còn hạn không bị ảnh hưởng."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, now: datetime) -> SessionPurgeReport:
        async with self._uow_factory() as uow:
            refresh = await uow.sessions.delete_expired(now, now - REVOKED_RETENTION)
            resets = await uow.resets.delete_expired(now)
            await uow.commit()
        return SessionPurgeReport(refresh_tokens=refresh, reset_tokens=resets)
