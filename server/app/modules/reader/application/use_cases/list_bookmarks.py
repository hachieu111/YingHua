from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.dto import BookmarkItem, BookmarkPage
from app.modules.reader.application.ports import ReaderUnitOfWork


class ListBookmarksUseCase:
    """F05.07 — Danh sách trang đã lưu của tôi, mới nhất trước, kèm truyện/chương/số trang (US-NH-63).

    Trang không còn đọc được (bị xóa, mất quyền) bị lược khỏi danh sách; `total` là số dấu trang đang lưu.
    Quản trị viên xem của người khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(
        self, identity: Identity, page: int, size: int, owner_id: int | None = None
    ) -> BookmarkPage:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            refs, total = await uow.annotations.list_bookmarked(owner, (page - 1) * size, size)
        described = {
            a.page_id: a for a in await self._pages.describe_pages(identity, [r.page_id for r in refs])
        }
        items = [BookmarkItem(described[r.page_id], r.updated_at) for r in refs if r.page_id in described]
        return BookmarkPage(items=items, total=total)
