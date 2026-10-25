from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.access import load_readable_bubble
from app.modules.reader.application.dto import EditedBubble
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.domain.rules import clean_edit_text


class SaveBubbleEditUseCase:
    """F05.05 — Người học nhập bản dịch riêng cho một bong bóng (US-NH-24).

    Bản sửa chỉ áp dụng cho chính người đó, không đổi dữ liệu dịch dùng chung; sửa lại thì ghi đè.
    """

    def __init__(
        self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity, bubble_id: int, text_vi: str) -> EditedBubble:
        text = clean_edit_text(text_vi)
        async with self._uow_factory() as uow:
            bubble = await load_readable_bubble(uow, self._pages, identity, bubble_id)
            await uow.edits.upsert(identity.user_id, bubble_id, text, self._clock.now())
            await uow.commit()
        return EditedBubble(bubble=bubble, edited_text=text)
