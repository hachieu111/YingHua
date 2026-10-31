from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    attach_progress,
    attach_vip_access,
    mark_editable,
    require_user,
)
from app.modules.library.application.dto import Paged
from app.modules.library.application.ports import LibraryUnitOfWork, SeriesFilter
from app.modules.library.domain.entities import LibraryTab, SeriesView


class ListLibraryUseCase:
    """F03.13 — Thư viện cá nhân theo tab Tất cả / Đang đọc / Yêu thích / Đã xong (US-NH-61).

    Truyện đã bị xóa hoặc không còn quyền đọc tự biến mất khỏi danh sách. Quản trị viên xem Thư viện của người
    khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(
        self, identity: Identity, tab: LibraryTab, page: int, size: int, owner_id: int | None = None
    ) -> Paged[SeriesView]:
        actor = actor_of(identity)
        require_user(actor)
        user_id = resolve_owner(identity, owner_id)
        flt = SeriesFilter(viewer_id=user_id, scope="library", tab=tab, include_empty=True)
        async with self._uow_factory() as uow:
            views, total = await uow.series.search(flt, (page - 1) * size, size)
            views = await attach_progress(uow, views, user_id)
            views = await attach_vip_access(uow, views, actor, self._clock.now())
        return Paged(mark_editable(views, actor), total)
