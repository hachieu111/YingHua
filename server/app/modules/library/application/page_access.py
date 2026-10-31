"""Kiểm quyền truy cập trang cho module khác (M04, M05) — F03.10."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.core.clock import Clock
from app.core.errors import DomainError, PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    can_edit_page,
    load_readable_page,
    load_readable_series,
)
from app.modules.library.application.dto import PageAccess, SeriesRef
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import PageContext
from app.modules.library.domain.errors import FileExpiredError

MAX_PAGES_PER_TRANSLATION_CHECK = 50


def _access(ctx: PageContext, can_edit: bool) -> PageAccess:
    page = ctx.page
    return PageAccess(
        page_id=page.id,
        page_no=page.page_no,
        translation_id=page.translation_id,
        original_file_id=page.original_file_id,
        width=page.width,
        height=page.height,
        can_edit=can_edit,
        chapter_id=ctx.chapter.id if ctx.chapter else None,
        chapter_number=ctx.chapter.number if ctx.chapter else None,
        series_id=ctx.series.id if ctx.series else None,
        series_title=ctx.series.title_vi if ctx.series else None,
    )


class LibraryPageAccess:
    """Cổng đọc trang có kiểm quyền.

    Lỗi: PageNotFoundError (không thấy hoặc không quyền xem), LoginRequiredError (Khách mở chương không đọc
    thử), FileExpiredError (ảnh tải nhanh hết hạn), PermissionDeniedError (cần quyền sửa mà không có).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def get_page(
        self, identity: Identity | None, page_id: int, *, require_edit: bool = False
    ) -> PageAccess:
        actor = actor_of(identity)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ctx = await load_readable_page(uow, page_id, actor, now)
        if ctx.page.expires_at is not None and ctx.page.expires_at <= now:
            raise FileExpiredError()
        can_edit = can_edit_page(ctx, actor)
        if require_edit and not can_edit:
            raise PermissionDeniedError()
        return _access(ctx, can_edit)

    async def can_read_translation(self, identity: Identity | None, translation_id: int) -> bool:
        """Có ít nhất một trang dùng bản dịch này mà người gọi được đọc (bong bóng thuộc bản dịch)."""
        actor = actor_of(identity)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            page_ids = await uow.pages.page_ids_for_translation(
                translation_id, MAX_PAGES_PER_TRANSLATION_CHECK
            )
            for page_id in page_ids:
                try:
                    ctx = await load_readable_page(uow, page_id, actor, now)
                except DomainError:
                    continue
                if ctx.page.expires_at is None or ctx.page.expires_at > now:
                    return True
        return False

    async def describe_pages(self, identity: Identity | None, page_ids: Sequence[int]) -> list[PageAccess]:
        """Thông tin các trang đọc được, giữ thứ tự đầu vào; bỏ qua trang không còn hoặc không có quyền."""
        actor = actor_of(identity)
        now = self._clock.now()
        result: list[PageAccess] = []
        async with self._uow_factory() as uow:
            for page_id in page_ids:
                try:
                    ctx = await load_readable_page(uow, page_id, actor, now)
                except DomainError:
                    continue
                result.append(_access(ctx, can_edit_page(ctx, actor)))
        return result

    async def readable_page_for_translation(
        self, identity: Identity | None, translation_id: int
    ) -> PageAccess | None:
        """Trang đầu tiên dùng bản dịch này mà người gọi đọc được (M07 cắt ảnh khi chưa biết trang)."""
        async with self._uow_factory() as uow:
            page_ids = await uow.pages.page_ids_for_translation(
                translation_id, MAX_PAGES_PER_TRANSLATION_CHECK
            )
        for page_id in page_ids:
            try:
                return await self.get_page(identity, page_id)
            except DomainError:
                continue
        return None

    async def series_of_pages(
        self, identity: Identity | None, page_ids: Sequence[int]
    ) -> dict[int, SeriesRef]:
        """Truyện đọc được của các trang; trang tải nhanh, đã xóa hoặc hết quyền đọc thì vắng mặt."""
        actor = actor_of(identity)
        async with self._uow_factory() as uow:
            series_of = await uow.pages.series_ids_of_pages(page_ids)
            refs: dict[int, SeriesRef] = {}
            for series_id in set(series_of.values()):
                try:
                    series = await load_readable_series(uow, series_id, actor)
                except DomainError:
                    continue
                refs[series_id] = SeriesRef(series.id, series.title_vi)
        return {page: refs[series] for page, series in series_of.items() if series in refs}

    async def page_ids_of_series(self, series_id: int) -> list[int]:
        """Mã trang của một truyện, không kiểm quyền: người gọi chỉ dùng để giao với dữ liệu của chính họ."""
        async with self._uow_factory() as uow:
            return await uow.pages.page_ids_for_series(series_id)
