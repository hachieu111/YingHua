"""Bề mặt công khai của M04 dành cho worker và tác vụ nền (F04.07, F04.13, F04.14, F15.03).

Worker (process riêng) gọi các hàm của `WorkerJobs`, hai giai đoạn (F04.02):

    job = await jobs.claim_next_job(worker_id, now)
    if job is not None:
        try:
            ...  # giai đoạn 1: đọc ảnh bằng storage.read(job.source_storage_key), OCR + dịch
            await jobs.save_text_result(job.translation_id, bubbles, partial_stats)  # đọc được ngay
            ...  # giai đoạn 2: xóa chữ + đắp chữ
            inpainted = await jobs.store_result_image(png_bytes, FileKind.INPAINTED)
            rendered = await jobs.store_result_image(png_bytes, FileKind.RENDERED)
            await jobs.complete_job(job.translation_id, JobResult(bubbles, inpainted, rendered, stats, ms))
        except Exception as exc:
            await jobs.fail_job(job.translation_id, "ocr", str(exc))
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.core.stored_files import FileKind
from app.modules.imaging.application.dto import ClaimedJob, JobConfig, JobResult
from app.modules.imaging.application.use_cases.claim_next_job import ClaimNextJobUseCase
from app.modules.imaging.application.use_cases.complete_job import CompleteJobUseCase
from app.modules.imaging.application.use_cases.fail_job import FailJobUseCase
from app.modules.imaging.application.use_cases.purge_orphan_results import PurgeOrphanResultFilesUseCase
from app.modules.imaging.application.use_cases.save_text_result import SaveTextResultUseCase
from app.modules.imaging.application.use_cases.store_result_image import StoreResultImageUseCase
from app.modules.imaging.domain.entities import NewBubble, TranslationStatus


class WorkerJobs:
    """Cổng của worker vào hàng đợi `translations`."""

    def __init__(
        self,
        claim: ClaimNextJobUseCase,
        complete: CompleteJobUseCase,
        fail: FailJobUseCase,
        store_image: StoreResultImageUseCase,
        save_text: SaveTextResultUseCase,
    ) -> None:
        self._claim = claim
        self._complete = complete
        self._fail = fail
        self._store_image = store_image
        self._save_text = save_text

    async def claim_next_job(self, worker_id: str, now: datetime) -> ClaimedJob | None:
        """Nhận việc cũ nhất (đặt `running`, `attempts + 1`); None khi hàng đợi rỗng."""
        return await self._claim.execute(worker_id, now)

    async def store_result_image(self, data: bytes, kind: FileKind) -> int:
        """Lưu ảnh dẫn xuất (`FileKind.INPAINTED` hoặc `FileKind.RENDERED`); trả `stored_files.id`."""
        return await self._store_image.execute(data, kind)

    async def save_text_result(
        self, translation_id: int, bubbles: Sequence[NewBubble], partial_stats: dict[str, Any]
    ) -> None:
        """Giai đoạn 1: thay bong bóng cũ bằng bong bóng mới (chưa có style), vẫn `running`."""
        await self._save_text.execute(translation_id, bubbles, partial_stats)

    async def complete_job(self, translation_id: int, result: JobResult) -> None:
        """Giai đoạn 2: cập nhật style bong bóng đã có (hoặc chèn nếu chưa) + gắn ảnh + đặt `done`."""
        await self._complete.execute(translation_id, result)

    async def fail_job(self, translation_id: int, error_step: str, error_message: str) -> TranslationStatus:
        """Ghi lỗi; trả `queued` (còn lượt thử) hoặc `failed`."""
        return await self._fail.execute(translation_id, error_step, error_message)


__all__ = [
    "ClaimedJob",
    "FileKind",
    "JobConfig",
    "JobResult",
    "NewBubble",
    "PurgeOrphanResultFilesUseCase",
    "TranslationStatus",
    "WorkerJobs",
]
