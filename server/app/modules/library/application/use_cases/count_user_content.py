from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, require_user
from app.modules.library.application.ports import LibraryUnitOfWork, SeriesFilter


@dataclass(frozen=True, slots=True)
class UserContentCounts:
    private_series: int
    quick_uploads: int


class CountUserContentUseCase:
    """F13.07 — Số truyện riêng và số ảnh tải nhanh của một người dùng (trang tổng quan)."""

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, owner_id: int) -> UserContentCounts:
        require_user(actor_of(identity))
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            _, series_total = await uow.series.search(SeriesFilter(viewer_id=owner, scope="mine"), 0, 1)
            _, upload_total = await uow.pages.list_quick_uploads(owner, 0, 1)
        return UserContentCounts(series_total, upload_total)
