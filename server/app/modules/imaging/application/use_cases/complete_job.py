from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.storage import FileStorage, StagedFiles
from app.modules.imaging.application.dto import JobResult
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import TranslationStatus
from app.modules.imaging.domain.errors import JobNotRunningError, TranslationNotFoundError
from app.modules.imaging.domain.rules import validate_bubbles


class CompleteJobUseCase:
    """F04.13, F04.01, F04.02 — Worker hoàn tất giai đoạn 2: ảnh dẫn xuất, style, thống kê; `done` (US-XL-07).

    Một giao dịch. Bong bóng đã ghi ở giai đoạn 1 (`SaveTextResultUseCase`) chỉ được cập nhật `style` theo
    `idx` (id giữ nguyên); chưa có bong bóng (caller cũ) thì chèn như trước. Ảnh dẫn xuất cũ (khi xử lý
    lại) bị xóa sau khi commit. Chỉ việc đang `running` mới được hoàn tất.
    """

    def __init__(
        self, uow_factory: Callable[[], ImagingUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, translation_id: int, result: JobResult) -> None:
        validate_bubbles(result.bubbles)
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                translation = await uow.translations.get_for_update(translation_id)
                if translation is None:
                    raise TranslationNotFoundError()
                if translation.status is not TranslationStatus.RUNNING:
                    raise JobNotRunningError()
                new_ids = {result.inpainted_file_id, result.rendered_file_id}
                old_ids = {translation.inpainted_file_id, translation.rendered_file_id} - new_ids - {None}
                if await uow.bubbles.count_by_translation(translation_id) > 0:
                    # Giai đoạn 1 đã ghi chữ: giữ id bong bóng vì người học có thể đã lưu từ/câu/ghi chú.
                    await uow.bubbles.update_styles(
                        translation_id, {b.idx: b.style for b in result.bubbles if b.style is not None}
                    )
                else:
                    await uow.bubbles.add_many(translation_id, result.bubbles)
                await uow.translations.mark_done(
                    translation_id,
                    result.inpainted_file_id,
                    result.rendered_file_id,
                    result.stats,
                    result.processing_ms,
                    result.phash,
                    self._clock.now(),
                )
                keys = await uow.files.delete_many([i for i in old_ids if i is not None])
                staged.delete_after_commit(keys)
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
