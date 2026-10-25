from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.dto import EditedBubble
from app.modules.reader.application.ports import ReaderUnitOfWork


class ListBubbleEditsUseCase:
    """F13.07 (xem F05.05) — Các bản sửa dịch riêng của một người trên một trang (chỉ bong bóng đã sửa)."""

    def __init__(self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(
        self, identity: Identity, page_id: int, owner_id: int | None = None
    ) -> list[EditedBubble]:
        owner = resolve_owner(identity, owner_id)
        access = await self._pages.get_page(identity, page_id)
        if access.translation_id is None:
            return []
        async with self._uow_factory() as uow:
            bubbles = await uow.bubbles.list_by_translation(access.translation_id)
            edits = await uow.edits.get_many(owner, [b.id for b in bubbles]) if bubbles else {}
        return [EditedBubble(b, edits[b.id]) for b in bubbles if b.id in edits]
