from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.domain.entities import Annotation


class SetBookmarkUseCase:
    """F05.07 — Đánh dấu / bỏ đánh dấu một trang đã lưu (US-NH-63). Giữ nguyên ghi chú trên trang."""

    def __init__(
        self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity, page_id: int, is_bookmarked: bool) -> Annotation:
        await self._pages.get_page(identity, page_id)
        async with self._uow_factory() as uow:
            annotation = await uow.annotations.set_bookmark(
                identity.user_id, page_id, is_bookmarked, self._clock.now()
            )
            await uow.commit()
        return annotation
