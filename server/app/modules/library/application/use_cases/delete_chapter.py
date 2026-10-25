from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    load_editable_chapter,
    purge_assets,
    record_admin_action,
)
from app.modules.library.application.ports import LibraryUnitOfWork


class DeleteChapterUseCase:
    """F03.09, F03.11 — Xóa chương kèm trang và ảnh liên quan; tiến độ đọc của chương bị bỏ (F03.12)."""

    def __init__(
        self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, identity: Identity, chapter_id: int) -> None:
        actor = actor_of(identity)
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                chapter, series = await load_editable_chapter(uow, chapter_id, actor)
                assets = await uow.pages.assets_of_chapter(chapter_id)
                await uow.chapters.delete(chapter_id)
                await purge_assets(uow, staged, assets)
                await record_admin_action(
                    uow,
                    actor,
                    series,
                    "chapter.delete",
                    "chapter",
                    chapter_id,
                    self._clock.now(),
                    {"number": str(chapter.number)},
                )
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
