from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, require_user
from app.modules.library.application.dto import Paged, PageView
from app.modules.library.application.page_views import build_page_views
from app.modules.library.application.ports import LibraryUnitOfWork


class ListQuickUploadsUseCase:
    """F03.13, F03.08 — Tab "Ảnh tải lên": ảnh tải nhanh của chính người gọi (US-NH-61 TC3).

    Quản trị viên xem của người khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, page: int, size: int, owner_id: int | None = None
    ) -> Paged[PageView]:
        require_user(actor_of(identity))
        user_id = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            pages, total = await uow.pages.list_quick_uploads(user_id, (page - 1) * size, size)
            views = await build_page_views(uow, pages, None, True)
        return Paged(views, total)
