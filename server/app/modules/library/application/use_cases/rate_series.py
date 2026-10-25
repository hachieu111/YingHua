from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, load_readable_series, require_user
from app.modules.library.application.dto import RatingResult
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.rules import validate_stars


class RateSeriesUseCase:
    """F03.14 — Chấm 1–5 sao cho truyện; chấm lại là sửa lượt cũ (US-NH-62)."""

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, series_id: int, stars: int) -> RatingResult:
        actor = actor_of(identity)
        user_id = require_user(actor)
        validate_stars(stars)
        async with self._uow_factory() as uow:
            await load_readable_series(uow, series_id, actor)
            await uow.ratings.upsert(user_id, series_id, stars, self._clock.now())
            summary = await uow.ratings.summary(series_id)
            await uow.commit()
        return RatingResult(stars, summary.average, summary.count)
