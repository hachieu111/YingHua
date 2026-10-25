from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Generic, TypeVar

from app.core.errors import DomainError
from app.modules.imaging.application.public import TranslationSummary
from app.modules.library.domain.entities import (
    Chapter,
    ChapterView,
    Page,
    ReadingProgress,
    ResumePoint,
    Series,
    SeriesView,
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Paged(Generic[T]):
    items: list[T]
    total: int


@dataclass(frozen=True, slots=True)
class SeriesDetail:
    view: SeriesView
    chapters: list[ChapterView]
    progress: ResumePoint | None
    my_rating: int | None


@dataclass(frozen=True, slots=True)
class PageView:
    page: Page
    series_id: int | None
    translation: TranslationSummary | None
    can_edit: bool


@dataclass(frozen=True, slots=True)
class ChapterDetail:
    chapter: Chapter
    series: Series
    pages: list[PageView]
    can_edit: bool
    progress: ReadingProgress | None


@dataclass(frozen=True, slots=True)
class UploadItemResult:
    filename: str | None
    page: PageView | None = None
    error: DomainError | None = None


@dataclass(frozen=True, slots=True)
class RatingResult:
    my_stars: int
    average: float | None
    count: int


@dataclass(frozen=True, slots=True)
class FileContent:
    data: bytes
    mime_type: str


@dataclass(frozen=True, slots=True)
class SeriesInput:
    """Dữ liệu tạo truyện (F03.04, F03.05)."""

    title_vi: str
    title_zh: str | None = None
    author: str | None = None
    description: str | None = None
    est_hsk_level: int | None = None
    genres: tuple[str, ...] = ()
    status: str = "ongoing"
    visibility: str = "private"
    confirm_duplicate: bool = False


@dataclass(frozen=True, slots=True)
class ChapterInput:
    number: Decimal
    title: str | None = None
    is_trial: bool = False


@dataclass(frozen=True, slots=True)
class ProgressInput:
    page_no: int
    mode: str = "read"
    completed: bool = False


@dataclass(frozen=True, slots=True)
class PageAccess:
    """Trang mà người gọi đã được kiểm quyền; module khác (M04, M05) dùng để khỏi truy cập bảng của M03."""

    page_id: int
    page_no: int
    translation_id: int | None
    original_file_id: int | None
    width: int | None
    height: int | None
    can_edit: bool
    chapter_id: int | None = None
    chapter_number: Decimal | None = None
    series_id: int | None = None
    series_title: str | None = None


@dataclass(frozen=True, slots=True)
class PurgeReport:
    pages: int
    files: int


@dataclass(frozen=True, slots=True)
class SeriesRef:
    """Truyện chứa một trang, dùng để nhóm từ đã lưu theo truyện (M07)."""

    series_id: int
    title: str


@dataclass(frozen=True, slots=True)
class ReadPageRef:
    """Một trang người học đã đọc: bản dịch (để lấy bong bóng) và tên truyện."""

    translation_id: int
    series_title: str


@dataclass(frozen=True, slots=True)
class SeriesCandidate:
    """Truyện công khai ứng viên để gợi ý theo trình độ (M10, F10.04)."""

    view: SeriesView
    library_count: int  # số người đã thêm vào Thư viện cá nhân
    finished: bool  # người gọi đã đọc hết mọi trang
