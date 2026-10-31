from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, can_edit_page, load_readable_page
from app.modules.library.application.dto import PageView
from app.modules.library.application.page_views import build_page_views
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.errors import FileExpiredError


class GetPageUseCase:
    """F03.08, F03.10, F04.02, F17.05 — Một trang kèm trạng thái xử lý. Ảnh tải nhanh chỉ chủ ảnh/admin xem.

    Trang thuộc chương VIP không đọc thử cần VIP còn hạn hoặc vé đã mở khóa truyện (403 `VIP_REQUIRED`).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity | None, page_id: int) -> PageView:
        actor = actor_of(identity)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ctx = await load_readable_page(uow, page_id, actor, now)
            if ctx.page.expires_at is not None and ctx.page.expires_at <= now:
                raise FileExpiredError()
            series_id = ctx.series.id if ctx.series else None
            (view,) = await build_page_views(uow, [ctx.page], series_id, can_edit_page(ctx, actor))
        return view
