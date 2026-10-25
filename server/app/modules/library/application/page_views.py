"""Dựng PageView (trang kèm trạng thái xử lý) cho các use case của M03."""

from __future__ import annotations

from app.modules.library.application.dto import PageView
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import Page


async def build_page_views(
    uow: LibraryUnitOfWork, pages: list[Page], series_id: int | None, can_edit: bool
) -> list[PageView]:
    ids = [p.translation_id for p in pages if p.translation_id is not None]
    summaries = await uow.translations.get_summaries(ids)
    return [
        PageView(
            page=p,
            series_id=series_id,
            translation=summaries.get(p.translation_id) if p.translation_id is not None else None,
            can_edit=can_edit,
        )
        for p in pages
    ]
