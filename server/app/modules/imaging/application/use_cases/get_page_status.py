from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.imaging.application.dto import PageStatus
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import TranslationStatus
from app.modules.library.application.public import PageAccessPort


class GetPageStatusUseCase:
    """F04.02 — Trạng thái xử lý của một trang để giao diện hỏi lại định kỳ (US-NH-18).

    Chỉ trang người gọi có quyền đọc (F03.10); trang `failed` kèm lý do và cờ cho phép dịch lại.
    `text_ready` = đã `done` hoặc đã có bong bóng (qua giai đoạn chữ) dù còn `running`/`failed`.
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(self, identity: Identity | None, page_id: int) -> PageStatus:
        access = await self._pages.get_page(identity, page_id)
        if access.translation_id is None:
            return PageStatus(page_id, None, None, 0, None, None, False)
        async with self._uow_factory() as uow:
            translation = await uow.translations.get(access.translation_id)
            has_bubbles = (
                translation is not None and await uow.bubbles.count_by_translation(translation.id) > 0
            )
        if translation is None:
            return PageStatus(page_id, access.translation_id, None, 0, None, None, False)
        return PageStatus(
            page_id=page_id,
            translation_id=translation.id,
            status=translation.status,
            attempts=translation.attempts,
            error_step=translation.error_step,
            error_message=translation.error_message,
            can_retranslate=access.can_edit and translation.status is TranslationStatus.FAILED,
            text_ready=translation.status is TranslationStatus.DONE or has_bubbles,
        )
