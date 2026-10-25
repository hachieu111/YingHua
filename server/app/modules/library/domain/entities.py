"""Thực thể của M03 Thư viện truyện — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class SeriesStatus(str, Enum):
    ONGOING = "ongoing"
    COMPLETED = "completed"


class ReadingMode(str, Enum):
    READ = "read"
    LEARN = "learn"


class LibraryTab(str, Enum):
    """Các tab của trang Thư viện (F03.13). Tab "Ảnh tải lên" dùng danh sách ảnh tải nhanh riêng."""

    ALL = "all"
    READING = "reading"
    FAVORITES = "favorites"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class Actor:
    """Người đang gọi: `user_id` là None khi là Khách (F01.09)."""

    user_id: int | None
    is_admin: bool = False

    @property
    def is_guest(self) -> bool:
        return self.user_id is None


@dataclass(slots=True)
class Series:
    id: int
    owner_id: int | None
    visibility: Visibility
    title_vi: str
    status: SeriesStatus
    created_at: datetime
    updated_at: datetime
    title_zh: str | None = None
    author: str | None = None
    description: str | None = None
    cover_file_id: int | None = None
    est_hsk_level: int | None = None
    created_by: int | None = None
    genres: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NewSeries:
    owner_id: int | None
    visibility: Visibility
    title_vi: str
    status: SeriesStatus
    created_by: int
    created_at: datetime
    title_zh: str | None = None
    author: str | None = None
    description: str | None = None
    est_hsk_level: int | None = None
    genres: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SeriesView:
    """Truyện kèm số liệu hiển thị trên thẻ truyện và trạng thái riêng của người xem."""

    series: Series
    chapter_count: int
    rating_avg: float | None
    rating_count: int
    in_library: bool
    is_favorite: bool
    can_edit: bool = False
    progress: SeriesProgress | None = None


@dataclass(slots=True)
class Chapter:
    id: int
    series_id: int
    number: Decimal
    is_trial: bool
    created_at: datetime
    updated_at: datetime
    title: str | None = None


@dataclass(frozen=True, slots=True)
class ChapterView:
    chapter: Chapter
    page_count: int


@dataclass(slots=True)
class Page:
    id: int
    chapter_id: int | None
    owner_id: int | None
    page_no: int
    created_at: datetime
    original_file_id: int | None = None
    translation_id: int | None = None
    width: int | None = None
    height: int | None = None
    expires_at: datetime | None = None  # chỉ có ở ảnh tải nhanh (F03.08)


@dataclass(frozen=True, slots=True)
class NewPage:
    chapter_id: int | None
    owner_id: int | None
    page_no: int
    created_at: datetime
    original_file_id: int
    translation_id: int
    width: int | None
    height: int | None


@dataclass(frozen=True, slots=True)
class PageContext:
    """Trang cùng truyện/chương chứa nó, để kiểm quyền (F03.10). Ảnh tải nhanh không có truyện/chương."""

    page: Page
    series: Series | None
    chapter: Chapter | None


@dataclass(frozen=True, slots=True)
class ReadingProgress:
    user_id: int
    chapter_id: int
    last_page_no: int
    mode: ReadingMode
    completed: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ResumePoint:
    """Vị trí "Tiếp tục đọc" của một truyện (F03.12). `page_no` đã quy về trang còn tồn tại gần nhất."""

    series_id: int
    chapter_id: int
    chapter_number: Decimal
    page_no: int
    page_id: int | None
    total_pages: int
    mode: ReadingMode
    completed: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SeriesProgress:
    """Tiến độ của một người trên một truyện: điểm dừng mới nhất (kể cả chương đã xong) + số trang đã đọc."""

    pages_read: int
    pages_total: int
    resume: ResumePoint | None = None

    @property
    def percent(self) -> int:
        if self.pages_total <= 0:
            return 0
        return min(100, round(self.pages_read * 100 / self.pages_total))


@dataclass(frozen=True, slots=True)
class ContinueItem:
    resume: ResumePoint
    series: Series
    chapter_title: str | None


@dataclass(frozen=True, slots=True)
class RatingSummary:
    average: float | None
    count: int


@dataclass(frozen=True, slots=True)
class FileContext:
    """Một nơi tệp được dùng, để quyết định ai được xem tệp (F03.10)."""

    is_cover: bool = False
    series_visibility: Visibility | None = None
    series_owner_id: int | None = None
    chapter_is_trial: bool | None = None
    page_owner_id: int | None = None  # chủ ảnh tải nhanh


@dataclass(frozen=True, slots=True)
class Assets:
    """Tệp và bản dịch cần dọn khi xóa truyện/chương/trang (F03.09)."""

    file_ids: tuple[int, ...] = ()
    translation_ids: tuple[int, ...] = ()
