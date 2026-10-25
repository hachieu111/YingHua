from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.imaging.application.dto import RequeueResult
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import Translation, TranslationStatus
from app.modules.imaging.domain.errors import (
    TranslationInProgressError,
    TranslationNotFailedError,
    TranslationNotFoundError,
)
from app.modules.library.application.public import PageAccessPort


def ensure_requeueable(translation: Translation) -> None:
    """Chỉ bản dịch `failed` được xếp hàng lại; đang chờ/đang xử lý thì báo đang xử lý (F04.03, F04.06)."""
    if translation.status in (TranslationStatus.QUEUED, TranslationStatus.RUNNING):
        raise TranslationInProgressError()
    if translation.status is not TranslationStatus.FAILED:
        raise TranslationNotFailedError()


class RetranslatePageUseCase:
    """F04.03 — Chủ trang (hoặc admin) đưa trang lỗi trở lại hàng đợi mà không tải ảnh lại (US-NH-21).

    Kiểm tra và đổi trạng thái là một thao tác nguyên tử (khóa dòng + UPDATE có điều kiện) nên không tạo việc
    trùng. Số lần thử được đặt lại, bong bóng cũ bị xóa.
    """

    def __init__(
        self, uow_factory: Callable[[], ImagingUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity, page_id: int) -> RequeueResult:
        access = await self._pages.get_page(identity, page_id, require_edit=True)
        if access.translation_id is None:
            raise TranslationNotFoundError()
        async with self._uow_factory() as uow:
            translation = await uow.translations.get_for_update(access.translation_id)
            if translation is None:
                raise TranslationNotFoundError()
            ensure_requeueable(translation)
            await uow.translations.requeue_failed(translation.id, self._clock.now())
            await uow.bubbles.delete_by_translation(translation.id)
            await uow.commit()
        return RequeueResult(
            page_id=page_id, translation_id=access.translation_id, status=TranslationStatus.QUEUED
        )
