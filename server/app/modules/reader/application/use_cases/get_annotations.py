from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.domain.entities import Annotation


class GetAnnotationsUseCase:
    """F13.07 (xem F05.07, F05.08) — Ghi chú và dấu trang của một trang; None nếu chưa có.

    Dành cho quản trị viên xem dữ liệu của người khác qua `owner_id`.
    """

    def __init__(self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(
        self, identity: Identity, page_id: int, owner_id: int | None = None
    ) -> Annotation | None:
        owner = resolve_owner(identity, owner_id)
        await self._pages.get_page(identity, page_id)
        async with self._uow_factory() as uow:
            return await uow.annotations.get(owner, page_id)
