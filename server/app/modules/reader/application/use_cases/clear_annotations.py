from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.ports import ReaderUnitOfWork


class ClearAnnotationsUseCase:
    """F05.08 — Xóa ghi chú trên trang (tô màu, nét vẽ), giữ dấu trang (US-NH-64). Gọi lặp không lỗi.

    Quản trị viên xóa của người khác qua `owner_id`, ghi nhật ký `user_data.annotation.delete` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity, page_id: int, owner_id: int | None = None) -> None:
        owner = resolve_owner(identity, owner_id)
        now = self._clock.now()
        await self._pages.get_page(identity, page_id)
        async with self._uow_factory() as uow:
            await uow.annotations.clear(owner, page_id, now)
            await record_admin_action(
                uow.audit, identity, owner, "user_data.annotation.delete", "page_annotation", page_id, now
            )
            await uow.commit()
