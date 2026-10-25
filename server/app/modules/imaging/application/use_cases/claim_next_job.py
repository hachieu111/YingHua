from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from app.modules.imaging.application.dto import ClaimedJob, JobConfig
from app.modules.imaging.application.ports import ImagingUnitOfWork

logger = logging.getLogger(__name__)

MAX_SKIPPED_JOBS = 20  # số việc hỏng (mất ảnh gốc) được đóng liên tiếp trong một lần nhận


class ClaimNextJobUseCase:
    """F04.07, F04.13 — Worker nhận việc cũ nhất (US-XL-01, US-XL-07).

    `SELECT ... FOR UPDATE SKIP LOCKED` nên hai worker không bao giờ nhận cùng một việc. Việc `running` bị
    bỏ quên quá `stale_after` được nhận lại; nếu đã hết lượt thử thì đóng `failed` thay vì chạy tiếp.
    Việc mất ảnh gốc được đóng `failed` rồi lấy việc kế tiếp.
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork], config: JobConfig) -> None:
        self._uow_factory = uow_factory
        self._config = config

    async def execute(self, worker_id: str, now: datetime) -> ClaimedJob | None:
        stale_before = now - self._config.stale_after
        for _ in range(MAX_SKIPPED_JOBS):
            async with self._uow_factory() as uow:
                closed = await uow.translations.fail_exhausted_stale(
                    stale_before, now, self._config.max_attempts
                )
                if closed:
                    logger.warning("Đóng %d việc treo đã hết lượt thử", closed)
                translation = await uow.translations.claim_next(worker_id, now, stale_before)
                if translation is None:
                    await uow.commit()
                    return None
                source = (
                    await uow.files.get(translation.source_file_id) if translation.source_file_id else None
                )
                if source is None or source.removed_at is not None:
                    await uow.translations.mark_failed(
                        translation.id, "source", "Không còn ảnh gốc để xử lý", False, now
                    )
                    await uow.commit()
                    continue
                await uow.commit()
                return ClaimedJob(
                    translation_id=translation.id,
                    source_file_id=source.id,
                    source_storage_key=source.storage_key,
                    source_mime_type=source.mime_type,
                    sha256=translation.sha256,
                    attempts=translation.attempts,
                    queued_at=translation.queued_at,
                )
        return None
