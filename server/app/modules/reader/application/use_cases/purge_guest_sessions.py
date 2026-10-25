from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.modules.reader.application.ports import ReaderUnitOfWork


class PurgeExpiredGuestSessionsUseCase:
    """F15.02 — Xóa phiên ẩn danh của Khách đã hết hạn (bộ đếm tra từ, F05.04). Trả số phiên đã xóa."""

    def __init__(self, uow_factory: Callable[[], ReaderUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, now: datetime) -> int:
        async with self._uow_factory() as uow:
            removed = await uow.guests.delete_expired(now)
            await uow.commit()
        return removed
