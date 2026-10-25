from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.core.image_validation import ImageUpload
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, require_user
from app.modules.library.application.dto import PageView
from app.modules.library.application.ingest import ingest_page_image
from app.modules.library.application.page_views import build_page_views
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import NewPage

QUICK_UPLOAD_PAGE_NO = 1


class QuickUploadUseCase:
    """F03.08 — Tải nhanh một ảnh lẻ không cần tạo truyện (US-NH-13).

    Ảnh thuộc riêng người tải, tự hết hạn sau `retention` (mặc định 7 ngày, F15.01 sẽ dọn).
    """

    def __init__(
        self,
        uow_factory: Callable[[], LibraryUnitOfWork],
        clock: Clock,
        storage: FileStorage,
        retention: timedelta,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage
        self._retention = retention

    async def execute(self, identity: Identity, upload: ImageUpload) -> PageView:
        user_id = require_user(actor_of(identity))
        now = self._clock.now()
        expires_at = now + self._retention
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                stored, translation_id = await ingest_page_image(
                    uow, staged, upload, user_id, now, expires_at
                )
                page = await uow.pages.add(
                    NewPage(
                        chapter_id=None,
                        owner_id=user_id,
                        page_no=QUICK_UPLOAD_PAGE_NO,
                        created_at=now,
                        original_file_id=stored.id,
                        translation_id=translation_id,
                        width=upload.info.width,
                        height=upload.info.height,
                    )
                )
                page.expires_at = expires_at
                (view,) = await build_page_views(uow, [page], None, True)
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        return view
