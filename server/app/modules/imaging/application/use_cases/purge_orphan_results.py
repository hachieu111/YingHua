from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from app.core.storage import FileStorage, StagedFiles
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.rules import ORPHAN_RESULT_GRACE_MINUTES

ORPHAN_BATCH_SIZE = 200
MAX_ORPHAN_BATCHES = 25


class PurgeOrphanResultFilesUseCase:
    """F15.03 — Dọn ảnh dẫn xuất (đã xóa chữ/đã dịch) không bản dịch nào tham chiếu.

    Sinh ra khi worker lưu ảnh xong nhưng không kịp `complete_job`. Chỉ xét tệp cũ hơn thời gian ân hạn để
    không xóa nhầm tệp worker vừa lưu. Không đụng tới ảnh gốc, bìa, avatar.
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork], storage: FileStorage) -> None:
        self._uow_factory = uow_factory
        self._storage = storage

    async def execute(self, now: datetime) -> int:
        created_before = now - timedelta(minutes=ORPHAN_RESULT_GRACE_MINUTES)
        removed = 0
        for _ in range(MAX_ORPHAN_BATCHES):
            staged = StagedFiles(self._storage)
            try:
                async with self._uow_factory() as uow:
                    ids = await uow.translations.orphan_result_file_ids(created_before, ORPHAN_BATCH_SIZE)
                    staged.delete_after_commit(await uow.files.delete_many(ids))
                    await uow.commit()
            except BaseException:
                await staged.discard()
                raise
            await staged.finalize()
            removed += len(ids)
            if len(ids) < ORPHAN_BATCH_SIZE:
                break
        return removed
