from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    load_readable_series,
    mark_editable,
    require_user,
)
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import SeriesView
from app.modules.library.domain.errors import SeriesNotFoundError


class AddToLibraryUseCase:
    """F03.13 — Thêm truyện vào Thư viện; thêm lặp không tạo bản ghi trùng (US-NH-61)."""

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, series_id: int) -> SeriesView:
        actor = actor_of(identity)
        user_id = require_user(actor)
        async with self._uow_factory() as uow:
            await load_readable_series(uow, series_id, actor)
            await uow.library.add(user_id, series_id, self._clock.now())
            view = await uow.series.get_view(series_id, user_id, False)
            if view is None:
                raise SeriesNotFoundError()
            await uow.commit()
        return mark_editable([view], actor)[0]
