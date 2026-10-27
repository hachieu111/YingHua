"""Giao diện (port) mà tầng hạ tầng của M03 phải hiện thực."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from app.core.stored_files import StoredFileRepository
from app.modules.imaging.application.public import TranslationRepository
from app.modules.library.domain.entities import (
    Assets,
    Chapter,
    ChapterView,
    ContinueItem,
    FileContext,
    LibraryTab,
    NewPage,
    NewSeries,
    Page,
    PageContext,
    RatingSummary,
    ReadingMode,
    ReadingProgress,
    ResumePoint,
    Series,
    SeriesProgress,
    SeriesView,
)
from app.modules.stats.application.public import ActivityRecorder


@dataclass(frozen=True, slots=True)
class SeriesFilter:
    """Điều kiện duyệt/tìm truyện (F03.02, F03.13). `viewer_id` None là Khách."""

    viewer_id: int | None
    scope: str  # "public" | "mine" | "library"
    query: str | None = None
    hsk: int | None = None
    hsk_min: int | None = None  # khoảng cấp HSK ước tính (F10.04)
    hsk_max: int | None = None
    genre: str | None = None
    include_empty: bool = False  # quản trị viên thấy cả truyện công khai chưa có chương
    trial_only: bool = False  # Khách chỉ thấy truyện có chương đọc thử
    tab: LibraryTab = LibraryTab.ALL


class SeriesRepository(Protocol):
    async def get(self, series_id: int) -> Series | None: ...

    async def add(self, new_series: NewSeries) -> Series: ...

    async def update(self, series: Series) -> None: ...

    async def delete(self, series_id: int) -> None: ...

    async def owner_has_title(self, owner_id: int, title_vi: str, exclude_id: int | None = None) -> bool:
        """Chủ này đã có truyện cùng tên (không phân biệt hoa thường) chưa."""
        ...

    async def search(self, flt: SeriesFilter, offset: int, limit: int) -> tuple[list[SeriesView], int]: ...

    async def get_view(
        self, series_id: int, viewer_id: int | None, trial_only: bool
    ) -> SeriesView | None: ...

    async def library_counts(self, series_ids: Sequence[int]) -> dict[int, int]:
        """Số người đã thêm từng truyện vào Thư viện cá nhân (độ phổ biến, F10.04)."""
        ...


class ChapterRepository(Protocol):
    async def get(self, chapter_id: int) -> Chapter | None: ...

    async def add(
        self, series_id: int, number: Decimal, title: str | None, is_trial: bool, now: datetime
    ) -> Chapter:
        """Raise ChapterNumberTakenError nếu số chương đã có trong truyện."""
        ...

    async def update(self, chapter: Chapter) -> None:
        """Raise ChapterNumberTakenError nếu đổi sang số đã có."""
        ...

    async def delete(self, chapter_id: int) -> None: ...

    async def list_for_series(self, series_id: int, trial_only: bool) -> list[ChapterView]: ...


class PageRepository(Protocol):
    async def get(self, page_id: int) -> Page | None: ...

    async def get_context(self, page_id: int) -> PageContext | None: ...

    async def list_for_chapter(self, chapter_id: int) -> list[Page]: ...

    async def lock_chapter_and_next_page_no(self, chapter_id: int) -> int:
        """Khóa dòng chương rồi trả số trang kế tiếp, để hai lượt tải đồng thời không trùng số."""
        ...

    async def chapter_has_sha256(self, chapter_id: int, sha256: str) -> bool: ...

    async def add(self, new_page: NewPage) -> Page: ...

    async def delete(self, page_id: int) -> None: ...

    async def list_quick_uploads(self, owner_id: int, offset: int, limit: int) -> tuple[list[Page], int]: ...

    async def page_numbers(self, chapter_id: int) -> list[int]: ...

    async def get_by_number(self, chapter_id: int, page_no: int) -> Page | None: ...

    async def assets_of_page(self, page_id: int) -> Assets: ...

    async def assets_of_chapter(self, chapter_id: int) -> Assets: ...

    async def assets_of_series(self, series_id: int) -> Assets:
        """Gồm cả ảnh bìa."""
        ...

    async def unreferenced_translation_ids(self, translation_ids: Sequence[int]) -> list[int]:
        """Trong `translation_ids`, những bản dịch không còn trang nào dùng."""
        ...

    async def page_ids_for_translation(self, translation_id: int, limit: int) -> list[int]:
        """Các trang dùng chung một bản dịch (ảnh trùng nội dung được dùng lại, F04.14)."""
        ...

    async def list_expired_quick_uploads(self, now: datetime, limit: int) -> list[int]:
        """Trang ảnh tải nhanh có ảnh gốc đã quá hạn lưu (F15.01)."""
        ...

    async def series_ids_of_pages(self, page_ids: Sequence[int]) -> dict[int, int]:
        """Truyện của từng trang (một truy vấn); trang tải nhanh hoặc không còn thì vắng mặt."""
        ...

    async def page_ids_for_series(self, series_id: int) -> list[int]:
        """Mã mọi trang của một truyện (cho bộ lọc theo truyện của M07)."""
        ...

    async def file_contexts(self, file_id: int, translation_ids: Sequence[int]) -> list[FileContext]:
        """Các nơi dùng tệp: làm ảnh bìa, ảnh gốc của trang, hoặc ảnh dẫn xuất của `translation_ids`."""
        ...


class ProgressRepository(Protocol):
    async def get(self, user_id: int, chapter_id: int) -> ReadingProgress | None: ...

    async def upsert(
        self,
        user_id: int,
        chapter_id: int,
        page_no: int,
        mode: ReadingMode,
        completed: bool,
        now: datetime,
    ) -> ReadingProgress: ...

    async def mark_page_read(self, user_id: int, page_id: int, now: datetime) -> bool:
        """Ghi trang đã đọc; ghi lặp không tạo bản ghi mới. True nếu đây là lần đọc đầu (F12.01)."""
        ...

    async def list_read_series(self, user_id: int, limit: int) -> list[tuple[Series, SeriesProgress]]:
        """Truyện đã đọc, mới đọc gần nhất trước, kèm số trang đã đọc/tổng (F12.02)."""
        ...

    async def latest_for_series(self, user_id: int, series_id: int) -> ResumePoint | None: ...

    async def list_continue(self, user_id: int, limit: int) -> list[ContinueItem]: ...

    async def summaries_for_series(
        self, user_id: int, series_ids: Sequence[int]
    ) -> dict[int, SeriesProgress]:
        """Tiến độ theo lô (kể cả chương đã xong); truyện chưa đọc không có trong kết quả (F03.12)."""
        ...

    async def move_after_page_deleted(
        self, chapter_id: int, deleted_page_no: int, new_page_no: int | None
    ) -> None:
        """Chuyển tiến độ đang trỏ tới trang đã xóa sang trang gần nhất; không còn trang thì xóa tiến độ."""
        ...


class LibraryRepository(Protocol):
    async def add(self, user_id: int, series_id: int, now: datetime) -> None:
        """Thêm vào Thư viện; đã có thì giữ nguyên (F03.13)."""
        ...

    async def remove(self, user_id: int, series_id: int) -> None: ...

    async def set_favorite(self, user_id: int, series_id: int, value: bool, now: datetime) -> None:
        """Tự thêm vào Thư viện nếu chưa có rồi đặt cờ yêu thích."""
        ...


class RatingRepository(Protocol):
    async def upsert(self, user_id: int, series_id: int, stars: int, now: datetime) -> None: ...

    async def get(self, user_id: int, series_id: int) -> int | None: ...

    async def summary(self, series_id: int) -> RatingSummary: ...


class AuditLog(Protocol):
    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None: ...


class LibraryUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def series(self) -> SeriesRepository: ...

    @property
    def chapters(self) -> ChapterRepository: ...

    @property
    def pages(self) -> PageRepository: ...

    @property
    def progress(self) -> ProgressRepository: ...

    @property
    def library(self) -> LibraryRepository: ...

    @property
    def ratings(self) -> RatingRepository: ...

    @property
    def files(self) -> StoredFileRepository: ...

    @property
    def translations(self) -> TranslationRepository: ...

    @property
    def audit(self) -> AuditLog: ...

    @property
    def activity(self) -> ActivityRecorder: ...

    async def __aenter__(self) -> LibraryUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
