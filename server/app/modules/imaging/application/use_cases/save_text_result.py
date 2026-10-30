from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import NewBubble, TranslationStatus
from app.modules.imaging.domain.errors import JobNotRunningError, TranslationNotFoundError
from app.modules.imaging.domain.rules import validate_bubbles


class SaveTextResultUseCase:
    """F04.02, F05.01 — Worker ghi kết quả giai đoạn 1 (chữ, dịch, tách từ) để người học đọc ngay.

    Một giao dịch: xóa bong bóng cũ (lần thử trước bị treo/lỗi rồi được nhận lại) rồi chèn bong bóng mới;
    trạng thái vẫn `running`, chưa có ảnh dẫn xuất. Bản dịch có bong bóng được coi là `text_ready`.
    Chỉ việc đang `running` mới ghi được.
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, translation_id: int, bubbles: Sequence[NewBubble], partial_stats: dict[str, Any]
    ) -> None:
        validate_bubbles(bubbles)
        async with self._uow_factory() as uow:
            translation = await uow.translations.get_for_update(translation_id)
            if translation is None:
                raise TranslationNotFoundError()
            if translation.status is not TranslationStatus.RUNNING:
                raise JobNotRunningError()
            await uow.bubbles.delete_by_translation(translation_id)
            await uow.bubbles.add_many(translation_id, bubbles)
            await uow.translations.save_partial_stats(translation_id, partial_stats)
            await uow.commit()
