"""Bề mặt công khai của M03 cho module khác (M04, M05, M15). Module khác chỉ import từ đây."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.auth.application.public import Identity
from app.modules.library.application.dto import (
    ChapterDetail,
    PageAccess,
    PageView,
    PurgeReport,
    ReadPageRef,
    SeriesCandidate,
    SeriesRef,
)
from app.modules.library.application.page_access import LibraryPageAccess
from app.modules.library.application.use_cases.count_user_content import (
    CountUserContentUseCase,
    UserContentCounts,
)
from app.modules.library.application.use_cases.get_chapter import GetChapterUseCase
from app.modules.library.application.use_cases.list_series_candidates import ListSeriesCandidatesUseCase
from app.modules.library.application.use_cases.purge_expired_uploads import PurgeExpiredQuickUploadsUseCase


class PageAccessPort(Protocol):
    """Kiểm quyền trang theo F03.10. Khách là `identity=None`."""

    async def get_page(
        self, identity: Identity | None, page_id: int, *, require_edit: bool = False
    ) -> PageAccess: ...

    async def can_read_translation(self, identity: Identity | None, translation_id: int) -> bool: ...

    async def describe_pages(
        self, identity: Identity | None, page_ids: Sequence[int]
    ) -> list[PageAccess]: ...

    async def readable_page_for_translation(
        self, identity: Identity | None, translation_id: int
    ) -> PageAccess | None: ...

    async def series_of_pages(
        self, identity: Identity | None, page_ids: Sequence[int]
    ) -> dict[int, SeriesRef]: ...

    async def page_ids_of_series(self, series_id: int) -> list[int]: ...


__all__ = [
    "ChapterDetail",
    "CountUserContentUseCase",
    "GetChapterUseCase",
    "LibraryPageAccess",
    "ListSeriesCandidatesUseCase",
    "PageAccess",
    "PageAccessPort",
    "PageView",
    "PurgeExpiredQuickUploadsUseCase",
    "PurgeReport",
    "ReadPageRef",
    "SeriesCandidate",
    "SeriesRef",
    "UserContentCounts",
]
