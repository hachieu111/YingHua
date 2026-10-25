from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.clock import Clock
from app.modules.imaging.application.dto import JobConfig
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import TranslationStatus
from app.modules.imaging.domain.errors import JobNotRunningError, TranslationNotFoundError
from app.modules.imaging.domain.rules import clip_error

logger = logging.getLogger(__name__)


class FailJobUseCase:
    """F04.13 — Worker báo lỗi của một việc (US-XL-07).

    Ghi bước lỗi và thông điệp (tối đa 1000 ký tự, không stack trace). Còn lượt thử (`attempts < max`) thì
    đưa lại `queued`, hết lượt thì `failed` để người dùng dịch lại (F04.03).
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork], clock: Clock, config: JobConfig) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._config = config

    async def execute(self, translation_id: int, error_step: str, error_message: str) -> TranslationStatus:
        step, message = clip_error(error_step, error_message)
        async with self._uow_factory() as uow:
            translation = await uow.translations.get_for_update(translation_id)
            if translation is None:
                raise TranslationNotFoundError()
            if translation.status is not TranslationStatus.RUNNING:
                raise JobNotRunningError()
            requeue = translation.attempts < self._config.max_attempts
            status = await uow.translations.mark_failed(
                translation_id, step, message, requeue, self._clock.now()
            )
            await uow.commit()
        logger.warning(
            "Việc xử lý ảnh %d lỗi ở bước %s (lần %d) → %s",
            translation_id,
            step,
            translation.attempts,
            status.value,
        )
        return status
