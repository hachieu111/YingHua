from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.image_validation import UploadAttempt
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    load_editable_chapter,
    record_admin_action,
    require_user,
)
from app.modules.library.application.dto import PageView, UploadItemResult
from app.modules.library.application.ingest import ingest_page_image
from app.modules.library.application.page_views import build_page_views
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import NewPage, Page
from app.modules.library.domain.errors import PageAlreadyExistsError, TooManyFilesError
from app.modules.library.domain.rules import MAX_FILES_PER_UPLOAD


class UploadPagesUseCase:
    """F03.07 — Tải một hoặc nhiều ảnh trang vào chương (US-NH-12).

    Mỗi ảnh hợp lệ tạo một trang `queued` và một bản dịch chờ worker (F04.01). Ảnh trùng nội dung trong cùng
    chương bị bỏ qua; một ảnh lỗi không làm hỏng các ảnh khác. Trả kết quả riêng cho từng tệp.
    """

    def __init__(
        self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(
        self, identity: Identity, chapter_id: int, attempts: list[UploadAttempt]
    ) -> list[UploadItemResult]:
        actor = actor_of(identity)
        user_id = require_user(actor)
        if len(attempts) > MAX_FILES_PER_UPLOAD:
            raise TooManyFilesError()
        now = self._clock.now()
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                chapter, series = await load_editable_chapter(uow, chapter_id, actor)
                page_no = await uow.pages.lock_chapter_and_next_page_no(chapter_id)
                created: dict[int, Page] = {}  # vị trí trong `attempts` -> trang đã tạo
                for position, attempt in enumerate(attempts):
                    upload = attempt.upload
                    if upload is None or await uow.pages.chapter_has_sha256(chapter_id, upload.info.sha256):
                        continue
                    stored, translation_id = await ingest_page_image(uow, staged, upload, user_id, now)
                    created[position] = await uow.pages.add(
                        NewPage(
                            chapter_id=chapter_id,
                            owner_id=user_id,
                            page_no=page_no,
                            created_at=now,
                            original_file_id=stored.id,
                            translation_id=translation_id,
                            width=upload.info.width,
                            height=upload.info.height,
                        )
                    )
                    page_no += 1
                views = await build_page_views(uow, list(created.values()), series.id, True)
                if created:
                    await record_admin_action(
                        uow, actor, series, "page.upload", "chapter", chapter.id, now, {"count": len(created)}
                    )
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        by_position = dict(zip(created, views, strict=True))
        return [_result(attempt, by_position.get(i)) for i, attempt in enumerate(attempts)]


def _result(attempt: UploadAttempt, view: PageView | None) -> UploadItemResult:
    if view is not None:
        return UploadItemResult(attempt.filename, page=view)
    return UploadItemResult(attempt.filename, error=attempt.error or PageAlreadyExistsError())
