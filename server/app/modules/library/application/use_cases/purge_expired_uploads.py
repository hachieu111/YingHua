from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.core.storage import FileStorage, StagedFiles
from app.modules.library.application.access import purge_assets
from app.modules.library.application.dto import PurgeReport
from app.modules.library.application.ports import LibraryUnitOfWork

PURGE_BATCH_SIZE = 100
MAX_PURGE_BATCHES = 50  # chặn một lần chạy kéo quá dài; phần còn lại để chu kỳ sau


class PurgeExpiredQuickUploadsUseCase:
    """F15.01, F03.08 — Xóa ảnh tải nhanh hết hạn kèm bản dịch không còn ai dùng và tệp (US-HG-01).

    Chỉ trang không thuộc chương (ảnh tải nhanh) có ảnh gốc `expires_at <= now`; ảnh của truyện không bao giờ
    bị dọn. Ảnh ngữ cảnh trong sổ tay là bản sao độc lập nên không bị ảnh hưởng. Mỗi lô là một giao dịch;
    tệp thật chỉ bị xóa sau khi lô đã commit.
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], storage: FileStorage) -> None:
        self._uow_factory = uow_factory
        self._storage = storage

    async def execute(self, now: datetime) -> PurgeReport:
        pages = files = 0
        for _ in range(MAX_PURGE_BATCHES):
            removed_pages, removed_files = await self._purge_batch(now)
            pages += removed_pages
            files += removed_files
            if removed_pages < PURGE_BATCH_SIZE:
                break
        return PurgeReport(pages=pages, files=files)

    async def _purge_batch(self, now: datetime) -> tuple[int, int]:
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                page_ids = await uow.pages.list_expired_quick_uploads(now, PURGE_BATCH_SIZE)
                files = 0
                for page_id in page_ids:
                    assets = await uow.pages.assets_of_page(page_id)
                    await uow.pages.delete(page_id)
                    files += await purge_assets(uow, staged, assets)
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        return len(page_ids), files
