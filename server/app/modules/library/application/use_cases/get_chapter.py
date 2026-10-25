from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.imaging.application.public import TranslationStatus
from app.modules.library.application.access import actor_of, load_readable_chapter
from app.modules.library.application.dto import ChapterDetail
from app.modules.library.application.page_views import build_page_views
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.rules import can_edit_series


class GetChapterUseCase:
    """F03.03, F03.10, F04.02 — Chương kèm danh sách trang và trạng thái xử lý (US-KH-04, US-NH-18).

    Khách chỉ mở được chương đọc thử của truyện công khai.
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity | None, chapter_id: int) -> ChapterDetail:
        actor = actor_of(identity)
        async with self._uow_factory() as uow:
            chapter, series = await load_readable_chapter(uow, chapter_id, actor)
            can_edit = can_edit_series(series, actor)
            pages = await build_page_views(
                uow, await uow.pages.list_for_chapter(chapter_id), series.id, can_edit
            )
            if actor.is_guest:  # Khách chỉ xem trang đã xử lý xong (F03.03)
                pages = [p for p in pages if p.translation and p.translation.status is TranslationStatus.DONE]
            progress = None
            if actor.user_id is not None:
                progress = await uow.progress.get(actor.user_id, chapter_id)
        return ChapterDetail(chapter, series, pages, can_edit, progress)
