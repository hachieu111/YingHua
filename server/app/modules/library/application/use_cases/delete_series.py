from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    load_editable_series,
    purge_assets,
    record_admin_action,
)
from app.modules.library.application.ports import LibraryUnitOfWork


class DeleteSeriesUseCase:
    """F03.09, F03.11 — Xóa truyện kèm chương, trang, ảnh liên quan (US-NH-14, US-QT-05).

    Từ đã lưu, ngữ cảnh ảnh cắt và thẻ của người học được giữ (liên kết SET NULL ở CSDL).
    """

    def __init__(
        self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, identity: Identity, series_id: int) -> None:
        actor = actor_of(identity)
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                series = await load_editable_series(uow, series_id, actor)
                assets = await uow.pages.assets_of_series(series_id)
                await uow.series.delete(series_id)
                await purge_assets(uow, staged, assets)
                await record_admin_action(
                    uow,
                    actor,
                    series,
                    "series.delete",
                    "series",
                    series_id,
                    self._clock.now(),
                    {"title": series.title_vi},
                )
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
