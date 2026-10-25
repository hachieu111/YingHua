from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    can_edit_page,
    load_readable_page,
    purge_assets,
    record_admin_action,
)
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.rules import nearest_page_no


class DeletePageUseCase:
    """F03.09, F03.11, F03.12 — Xóa một trang (hoặc ảnh tải nhanh) kèm ảnh liên quan (US-NH-14).

    Tiến độ đang trỏ tới trang này được chuyển sang trang gần nhất còn tồn tại. Từ đã lưu giữ nguyên.
    """

    def __init__(
        self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, identity: Identity, page_id: int) -> None:
        actor = actor_of(identity)
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                ctx = await load_readable_page(uow, page_id, actor)
                if not can_edit_page(ctx, actor):
                    raise PermissionDeniedError()
                assets = await uow.pages.assets_of_page(page_id)
                await uow.pages.delete(page_id)
                if ctx.chapter is not None:
                    remaining = await uow.pages.page_numbers(ctx.chapter.id)
                    target = nearest_page_no(remaining, ctx.page.page_no)
                    await uow.progress.move_after_page_deleted(ctx.chapter.id, ctx.page.page_no, target)
                await purge_assets(uow, staged, assets)
                if ctx.series is not None:
                    await record_admin_action(
                        uow, actor, ctx.series, "page.delete", "page", page_id, self._clock.now()
                    )
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
