from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.access import load_readable_bubble
from app.modules.reader.application.ports import ReaderUnitOfWork


class DeleteBubbleEditUseCase:
    """F05.06 — Hoàn tác bản sửa dịch, trở về bản dịch gốc (US-NH-25). Gọi lặp không lỗi.

    Quản trị viên hoàn tác bản sửa của người khác qua `owner_id`, ghi nhật ký
    `user_data.bubble_edit.delete` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity, bubble_id: int, owner_id: int | None = None) -> None:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            await load_readable_bubble(uow, self._pages, identity, bubble_id)
            if await uow.edits.delete(owner, bubble_id):
                await record_admin_action(
                    uow.audit,
                    identity,
                    owner,
                    "user_data.bubble_edit.delete",
                    "bubble_edit",
                    bubble_id,
                    self._clock.now(),
                )
            await uow.commit()
