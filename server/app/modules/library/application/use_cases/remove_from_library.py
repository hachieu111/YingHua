from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, require_user
from app.modules.library.application.ports import LibraryUnitOfWork


class RemoveFromLibraryUseCase:
    """F03.13 — Bỏ truyện khỏi Thư viện; không xóa tiến độ đọc, sổ tay hay thẻ (US-NH-61)."""

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, series_id: int) -> None:
        user_id = require_user(actor_of(identity))
        async with self._uow_factory() as uow:
            await uow.library.remove(user_id, series_id)
            await uow.commit()
