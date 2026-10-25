from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, require_user
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import ContinueItem


class ListContinueReadingUseCase:
    """F03.12 — Danh sách truyện đang đọc dở, mới nhất trước, kèm vị trí "Tiếp tục đọc" (US-NH-16).

    Quản trị viên xem tiến độ của người khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, limit: int, owner_id: int | None = None
    ) -> list[ContinueItem]:
        require_user(actor_of(identity))
        user_id = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            return await uow.progress.list_continue(user_id, limit)
