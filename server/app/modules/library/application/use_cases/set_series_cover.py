from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.image_validation import ImageUpload
from app.core.storage import FileStorage, StagedFiles
from app.core.stored_files import FileKind, store_image
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    load_editable_series,
    mark_editable,
    record_admin_action,
)
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import SeriesView
from app.modules.library.domain.errors import SeriesNotFoundError


class SetSeriesCoverUseCase:
    """F03.04, F03.09 — Đặt hoặc thay ảnh bìa truyện; ảnh bìa cũ bị xóa (US-NH-10)."""

    def __init__(
        self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, identity: Identity, series_id: int, upload: ImageUpload) -> SeriesView:
        actor = actor_of(identity)
        now = self._clock.now()
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                series = await load_editable_series(uow, series_id, actor)
                stored = await store_image(staged, uow.files, upload, FileKind.COVER, actor.user_id, now)
                old_id = series.cover_file_id
                series.cover_file_id = stored.id
                await uow.series.update(series)
                if old_id is not None:
                    staged.delete_after_commit(await uow.files.delete_many([old_id]))
                await record_admin_action(uow, actor, series, "series.cover", "series", series.id, now)
                view = await uow.series.get_view(series.id, actor.user_id, False)
                if view is None:
                    raise SeriesNotFoundError()
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        return mark_editable([view], actor)[0]
