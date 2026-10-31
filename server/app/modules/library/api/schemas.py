from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.core.uploads import file_url
from app.modules.library.application.dto import (
    ChapterDetail,
    PageView,
    RatingResult,
    SeriesDetail,
    UploadItemResult,
)
from app.modules.library.domain.entities import (
    Chapter,
    ChapterView,
    ContinueItem,
    ReadingProgress,
    ResumePoint,
    SeriesProgress,
    SeriesView,
)

ChapterNumber = Annotated[Decimal, Field(ge=0, le=Decimal("99999.9"), max_digits=6, decimal_places=1)]


class CreateSeriesRequest(BaseModel):
    title_vi: str = Field(max_length=255)
    title_zh: str | None = Field(default=None, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    est_hsk_level: int | None = Field(default=None, ge=1, le=9)
    genres: list[str] = Field(default_factory=list, max_length=8)
    status: Literal["ongoing", "completed"] = "ongoing"
    visibility: Literal["public", "private"] = "private"
    confirm_duplicate: bool = False


class UpdateSeriesRequest(BaseModel):
    title_vi: str | None = Field(default=None, max_length=255)
    title_zh: str | None = Field(default=None, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    est_hsk_level: int | None = Field(default=None, ge=1, le=9)
    genres: list[str] | None = Field(default=None, max_length=8)
    status: Literal["ongoing", "completed"] | None = None
    visibility: Literal["public", "private"] | None = None


class CreateChapterRequest(BaseModel):
    number: ChapterNumber
    title: str | None = Field(default=None, max_length=255)
    is_trial: bool = False


class UpdateChapterRequest(BaseModel):
    number: ChapterNumber | None = None
    title: str | None = Field(default=None, max_length=255)
    is_trial: bool | None = None


class SaveProgressRequest(BaseModel):
    page_no: int = Field(ge=1, le=32767)
    mode: Literal["read", "learn"] = "read"
    completed: bool = False


class RatingRequest(BaseModel):
    stars: int  # khoảng 1–5 được kiểm ở use case để trả mã INVALID_RATING


class FavoriteRequest(BaseModel):
    is_favorite: bool


class SeriesProgressResponse(BaseModel):
    """Tiến độ của người gọi trên một truyện; các trường điểm dừng là null nếu chưa có dòng tiến độ."""

    chapter_id: int | None
    chapter_number: float | None
    page_no: int | None
    page_id: int | None
    total_pages: int | None
    mode: str | None
    completed: bool
    updated_at: datetime | None
    pages_read: int
    pages_total: int
    percent: int

    @classmethod
    def from_progress(cls, p: SeriesProgress) -> SeriesProgressResponse:
        r = p.resume
        return cls(
            chapter_id=r.chapter_id if r else None,
            chapter_number=float(r.chapter_number) if r else None,
            page_no=r.page_no if r else None,
            page_id=r.page_id if r else None,
            total_pages=r.total_pages if r else None,
            mode=r.mode.value if r else None,
            completed=r.completed if r else False,
            updated_at=r.updated_at if r else None,
            pages_read=p.pages_read,
            pages_total=p.pages_total,
            percent=p.percent,
        )


class SeriesResponse(BaseModel):
    id: int
    title_vi: str
    title_zh: str | None
    author: str | None
    description: str | None
    cover_url: str | None
    visibility: str
    status: str
    est_hsk_level: int | None
    genres: list[str]
    owner_id: int | None
    chapter_count: int
    rating_avg: float | None
    rating_count: int
    in_library: bool
    is_favorite: bool
    can_edit: bool
    is_vip: bool = Field(description="Truyện VIP: người không VIP chỉ đọc chương đọc thử (F17.05)")
    vip_access: Literal["open", "trial_only", "unlocked", "vip"] = Field(
        description="Quyền truy cập của người gọi: open (truyện thường), trial_only, unlocked (đã mở khóa "
        "bằng vé), vip (đang VIP hoặc quản trị viên)"
    )
    progress: SeriesProgressResponse | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(cls, view: SeriesView) -> SeriesResponse:
        s = view.series
        return cls(
            id=s.id,
            title_vi=s.title_vi,
            title_zh=s.title_zh,
            author=s.author,
            description=s.description,
            cover_url=file_url(s.cover_file_id),
            visibility=s.visibility.value,
            status=s.status.value,
            est_hsk_level=s.est_hsk_level,
            genres=list(s.genres),
            owner_id=s.owner_id,
            chapter_count=view.chapter_count,
            rating_avg=view.rating_avg,
            rating_count=view.rating_count,
            in_library=view.in_library,
            is_favorite=view.is_favorite,
            can_edit=view.can_edit,
            is_vip=s.is_vip,
            vip_access=view.vip_access.value,
            progress=SeriesProgressResponse.from_progress(view.progress) if view.progress else None,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )


class SeriesPage(BaseModel):
    items: list[SeriesResponse]
    total: int
    page: int
    size: int


class ChapterResponse(BaseModel):
    id: int
    series_id: int
    number: float
    title: str | None
    is_trial: bool
    is_locked: bool = Field(
        default=False, description="Chương của truyện VIP mà người gọi chưa có quyền đọc (F17.05)"
    )
    page_count: int
    created_at: datetime

    @classmethod
    def from_chapter(cls, chapter: Chapter, page_count: int = 0, is_locked: bool = False) -> ChapterResponse:
        return cls(
            id=chapter.id,
            series_id=chapter.series_id,
            number=float(chapter.number),
            title=chapter.title,
            is_trial=chapter.is_trial,
            is_locked=is_locked,
            page_count=page_count,
            created_at=chapter.created_at,
        )

    @classmethod
    def from_view(cls, view: ChapterView) -> ChapterResponse:
        return cls.from_chapter(view.chapter, view.page_count, view.is_locked)


class ResumeResponse(BaseModel):
    series_id: int
    chapter_id: int
    chapter_number: float
    page_no: int
    page_id: int | None
    total_pages: int
    mode: str
    completed: bool
    updated_at: datetime

    @classmethod
    def from_resume(cls, r: ResumePoint) -> ResumeResponse:
        return cls(
            series_id=r.series_id,
            chapter_id=r.chapter_id,
            chapter_number=float(r.chapter_number),
            page_no=r.page_no,
            page_id=r.page_id,
            total_pages=r.total_pages,
            mode=r.mode.value,
            completed=r.completed,
            updated_at=r.updated_at,
        )


class SeriesDetailResponse(BaseModel):
    series: SeriesResponse
    chapters: list[ChapterResponse]
    progress: ResumeResponse | None
    my_rating: int | None

    @classmethod
    def from_detail(cls, d: SeriesDetail) -> SeriesDetailResponse:
        return cls(
            series=SeriesResponse.from_view(d.view),
            chapters=[ChapterResponse.from_view(c) for c in d.chapters],
            progress=ResumeResponse.from_resume(d.progress) if d.progress else None,
            my_rating=d.my_rating,
        )


class PageResponse(BaseModel):
    id: int
    chapter_id: int | None
    series_id: int | None
    page_no: int
    width: int | None
    height: int | None
    status: str | None
    text_ready: bool = Field(
        description="Chữ và bản dịch đã sẵn sàng (đã `done` hoặc đã có bong bóng dù còn running/failed)"
    )
    error_step: str | None
    error_message: str | None
    original_url: str | None
    inpainted_url: str | None
    rendered_url: str | None
    expires_at: datetime | None
    can_edit: bool
    created_at: datetime

    @classmethod
    def from_view(cls, v: PageView) -> PageResponse:
        p, t = v.page, v.translation
        return cls(
            id=p.id,
            chapter_id=p.chapter_id,
            series_id=v.series_id,
            page_no=p.page_no,
            width=p.width,
            height=p.height,
            status=t.status.value if t else None,
            text_ready=t.text_ready if t else False,
            error_step=t.error_step if t else None,
            error_message=t.error_message if t else None,
            original_url=file_url(p.original_file_id),
            inpainted_url=file_url(t.inpainted_file_id) if t else None,
            rendered_url=file_url(t.rendered_file_id) if t else None,
            expires_at=p.expires_at,
            can_edit=v.can_edit,
            created_at=p.created_at,
        )


class QuickUploadPage(BaseModel):
    items: list[PageResponse]
    total: int
    page: int
    size: int


class ProgressResponse(BaseModel):
    chapter_id: int
    page_no: int
    mode: str
    completed: bool
    updated_at: datetime

    @classmethod
    def from_progress(cls, p: ReadingProgress) -> ProgressResponse:
        return cls(
            chapter_id=p.chapter_id,
            page_no=p.last_page_no,
            mode=p.mode.value,
            completed=p.completed,
            updated_at=p.updated_at,
        )


class ChapterDetailResponse(BaseModel):
    chapter: ChapterResponse
    series_id: int
    series_title: str
    pages: list[PageResponse]
    can_edit: bool
    progress: ProgressResponse | None

    @classmethod
    def from_detail(cls, d: ChapterDetail) -> ChapterDetailResponse:
        return cls(
            chapter=ChapterResponse.from_chapter(d.chapter, len(d.pages)),
            series_id=d.series.id,
            series_title=d.series.title_vi,
            pages=[PageResponse.from_view(p) for p in d.pages],
            can_edit=d.can_edit,
            progress=ProgressResponse.from_progress(d.progress) if d.progress else None,
        )


class UploadErrorResponse(BaseModel):
    code: str
    message: str


class UploadItemResponse(BaseModel):
    filename: str | None
    page: PageResponse | None
    error: UploadErrorResponse | None

    @classmethod
    def from_result(cls, r: UploadItemResult) -> UploadItemResponse:
        return cls(
            filename=r.filename,
            page=PageResponse.from_view(r.page) if r.page else None,
            error=UploadErrorResponse(code=r.error.code, message=r.error.message) if r.error else None,
        )


class UploadPagesResponse(BaseModel):
    results: list[UploadItemResponse]
    created: int


class ContinueItemResponse(BaseModel):
    series_id: int
    series_title: str
    cover_url: str | None
    chapter_id: int
    chapter_number: float
    chapter_title: str | None
    page_no: int
    page_id: int | None
    total_pages: int
    mode: str
    updated_at: datetime

    @classmethod
    def from_item(cls, i: ContinueItem) -> ContinueItemResponse:
        r = i.resume
        return cls(
            series_id=i.series.id,
            series_title=i.series.title_vi,
            cover_url=file_url(i.series.cover_file_id),
            chapter_id=r.chapter_id,
            chapter_number=float(r.chapter_number),
            chapter_title=i.chapter_title,
            page_no=r.page_no,
            page_id=r.page_id,
            total_pages=r.total_pages,
            mode=r.mode.value,
            updated_at=r.updated_at,
        )


class RatingResponse(BaseModel):
    my_stars: int
    rating_avg: float | None
    rating_count: int

    @classmethod
    def from_result(cls, r: RatingResult) -> RatingResponse:
        return cls(my_stars=r.my_stars, rating_avg=r.average, rating_count=r.count)
