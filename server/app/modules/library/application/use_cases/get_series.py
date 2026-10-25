from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    attach_progress,
    load_readable_series,
    mark_editable,
)
from app.modules.library.application.dto import SeriesDetail
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.errors import SeriesNotFoundError


class GetSeriesUseCase:
    """F03.02, F03.03, F03.10, F03.12, F03.14 — Chi tiết truyện: chương, tiến độ, điểm sao, Thư viện.

    Khách chỉ thấy truyện công khai và các chương đọc thử (US-KH-04).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity | None, series_id: int) -> SeriesDetail:
        actor = actor_of(identity)
        async with self._uow_factory() as uow:
            await load_readable_series(uow, series_id, actor)
            view = await uow.series.get_view(series_id, actor.user_id, actor.is_guest)
            if view is None:
                raise SeriesNotFoundError()
            (view,) = await attach_progress(uow, [view], actor.user_id)
            chapters = await uow.chapters.list_for_series(series_id, trial_only=actor.is_guest)
            progress = my_rating = None
            if actor.user_id is not None:
                progress = await uow.progress.latest_for_series(actor.user_id, series_id)
                my_rating = await uow.ratings.get(actor.user_id, series_id)
        return SeriesDetail(mark_editable([view], actor)[0], chapters, progress, my_rating)
