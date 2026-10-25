from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.imaging.application.dto import RequeueResult
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.application.use_cases.retranslate_page import ensure_requeueable
from app.modules.imaging.domain.entities import TranslationStatus
from app.modules.imaging.domain.errors import TranslationNotFoundError


class RetryTranslationUseCase:
    """F04.06 — Quản trị viên chạy lại một bản dịch lỗi (US-QT-07).

    Chỉ bản dịch `failed`; lý do lỗi cũ bị xóa và lần chạy lại ghi đè lý do mới nếu vẫn lỗi. Ghi nhật ký
    quản trị (F13.06).
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, admin: Identity, translation_id: int) -> RequeueResult:
        if not admin.is_admin:
            raise PermissionDeniedError()
        now = self._clock.now()
        async with self._uow_factory() as uow:
            translation = await uow.translations.get_for_update(translation_id)
            if translation is None:
                raise TranslationNotFoundError()
            ensure_requeueable(translation)
            await uow.translations.requeue_failed(translation_id, now)
            await uow.bubbles.delete_by_translation(translation_id)
            await uow.audit.add(
                admin.user_id,
                "translation.retry",
                "translation",
                translation_id,
                {"error_step": translation.error_step},
                now,
            )
            await uow.commit()
        return RequeueResult(page_id=None, translation_id=translation_id, status=TranslationStatus.QUEUED)
