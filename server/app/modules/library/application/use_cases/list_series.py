from __future__ import annotations

from collections.abc import Callable

from app.core.errors import InvalidInputError
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, attach_progress, mark_editable, require_user
from app.modules.library.application.dto import Paged
from app.modules.library.application.ports import LibraryUnitOfWork, SeriesFilter
from app.modules.library.domain.entities import SeriesView

SCOPES = frozenset({"public", "mine"})


class ListSeriesUseCase:
    """F03.02 — Duyệt và tìm truyện (US-NH-09, US-KH-04).

    `public`: truyện công khai có ít nhất một chương (Khách: chỉ truyện có chương đọc thử; admin: thấy cả
    truyện
    chưa có chương). `mine`: truyện riêng tư của chính người gọi.
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self,
        identity: Identity | None,
        scope: str,
        query: str | None,
        hsk: int | None,
        genre: str | None,
        page: int,
        size: int,
    ) -> Paged[SeriesView]:
        if scope not in SCOPES:
            raise InvalidInputError("Phạm vi duyệt không hợp lệ")
        actor = actor_of(identity)
        if scope == "mine":
            require_user(actor)
        flt = SeriesFilter(
            viewer_id=actor.user_id,
            scope=scope,
            query=(query or "").strip() or None,
            hsk=hsk,
            genre=(genre or "").strip() or None,
            include_empty=actor.is_admin,
            trial_only=actor.is_guest,
        )
        async with self._uow_factory() as uow:
            views, total = await uow.series.search(flt, (page - 1) * size, size)
            views = await attach_progress(uow, views, actor.user_id)
        return Paged(mark_editable(views, actor), total)
