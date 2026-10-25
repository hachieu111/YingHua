from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.imaging.application.public import TranslationStatus
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.dto import ReadingBubble, ReadingView
from app.modules.reader.application.ports import ReaderUnitOfWork


class GetReadingUseCase:
    """F05.01 — Dữ liệu để vẽ trang ở ba dạng hiển thị kèm lớp Hover (US-NH-19, US-KH-04).

    Kiểm quyền đọc trang (F03.10; Khách chỉ chương đọc thử). Bong bóng chỉ có khi trang `done`; mỗi bong
    bóng mang bản dịch hiệu lực = bản sửa riêng của người gọi nếu có (F05.05). Ghi chú/dấu trang chỉ của
    người đã đăng nhập (F05.07, F05.08).
    """

    def __init__(self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(self, identity: Identity | None, page_id: int) -> ReadingView:
        access = await self._pages.get_page(identity, page_id)
        async with self._uow_factory() as uow:
            summary = None
            bubbles: list[ReadingBubble] = []
            if access.translation_id is not None:
                summaries = await uow.translations.get_summaries([access.translation_id])
                summary = summaries.get(access.translation_id)
                if summary is not None and summary.status is TranslationStatus.DONE:
                    raw = await uow.bubbles.list_by_translation(access.translation_id)
                    edits = (
                        await uow.edits.get_many(identity.user_id, [b.id for b in raw])
                        if identity is not None and raw
                        else {}
                    )
                    bubbles = [ReadingBubble(b, edits.get(b.id)) for b in raw]
            annotation = (
                await uow.annotations.get(identity.user_id, page_id) if identity is not None else None
            )
        return ReadingView(access=access, translation=summary, bubbles=bubbles, annotation=annotation)
