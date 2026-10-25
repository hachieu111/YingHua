from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.uploads import file_url
from app.modules.suggestions.application.dto import (
    ChapterCoverage,
    DismissedItem,
    DismissedPage,
    SeriesRecommendations,
    SuggestionList,
)
from app.modules.suggestions.domain.entities import SeriesRecommendation, Suggestion
from app.modules.suggestions.domain.rules import MAX_TERM_CHARS


class SuggestionItemResponse(BaseModel):
    term: str
    pinyin: str | None
    meaning_vi: str | None = Field(description="Nghĩa ngắn từ từ điển")
    hsk_level: int | None
    occurrences: int = Field(description="Số lần xuất hiện trong chương")
    lookups: int = Field(description="Số lần người học đã tra từ này")
    score: float
    bubble_id: int = Field(description="Bong bóng của lần xuất hiện đầu tiên (ngữ cảnh khi nhận)")
    page_id: int
    page_no: int

    @classmethod
    def from_item(cls, s: Suggestion) -> SuggestionItemResponse:
        return cls(
            term=s.term,
            pinyin=s.pinyin,
            meaning_vi=s.meaning_vi,
            hsk_level=s.hsk_level,
            occurrences=s.occurrences,
            lookups=s.lookups,
            score=s.score,
            bubble_id=s.bubble_id,
            page_id=s.page_id,
            page_no=s.page_no,
        )


class SuggestionListResponse(BaseModel):
    status: str = Field(description="ready | processing (còn trang chưa dịch xong)")
    hsk_level: int | None = Field(description="Trình độ đã khai báo; null thì giao diện nhắc khai báo")
    items: list[SuggestionItemResponse]

    @classmethod
    def from_list(cls, r: SuggestionList) -> SuggestionListResponse:
        return cls(
            status=r.status,
            hsk_level=r.hsk_level,
            items=[SuggestionItemResponse.from_item(s) for s in r.items],
        )


class AcceptSuggestionRequest(BaseModel):
    term: str = Field(min_length=1, max_length=64, description=f"Từ gợi ý, tối đa {MAX_TERM_CHARS} ký tự")


class DismissedItemResponse(BaseModel):
    term: str
    dismissed_at: datetime
    pinyin: str | None
    meaning_vi: str | None
    hsk_level: int | None

    @classmethod
    def from_item(cls, i: DismissedItem) -> DismissedItemResponse:
        return cls(
            term=i.dismissed.term,
            dismissed_at=i.dismissed.dismissed_at,
            pinyin=i.pinyin,
            meaning_vi=i.meaning_vi,
            hsk_level=i.hsk_level,
        )


class DismissedPageResponse(BaseModel):
    items: list[DismissedItemResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, p: DismissedPage, page: int, size: int) -> DismissedPageResponse:
        return cls(
            items=[DismissedItemResponse.from_item(i) for i in p.items], total=p.total, page=page, size=size
        )


class RecommendedSeriesResponse(BaseModel):
    id: int
    title_vi: str
    title_zh: str | None
    cover_url: str | None
    est_hsk_level: int | None
    genres: list[str]
    rating_avg: float | None
    rating_count: int
    chapter_count: int
    reason: str = Field(description="Lý do gợi ý, tiếng Việt")

    @classmethod
    def from_recommendation(cls, r: SeriesRecommendation) -> RecommendedSeriesResponse:
        c = r.candidate
        return cls(
            id=c.series_id,
            title_vi=c.title_vi,
            title_zh=c.title_zh,
            cover_url=file_url(c.cover_file_id),
            est_hsk_level=c.est_hsk_level,
            genres=list(c.genres),
            rating_avg=c.rating_avg,
            rating_count=c.rating_count,
            chapter_count=c.chapter_count,
            reason=r.reason,
        )


class SeriesRecommendationsResponse(BaseModel):
    hsk_level: int | None = Field(description="Trình độ đã khai báo; null thì giao diện nhắc khai báo")
    needs_level: bool = Field(description="true khi chưa khai báo trình độ HSK (F02.01)")
    items: list[RecommendedSeriesResponse] = Field(description="0–3 truyện; rỗng thì hiện thông báo chưa có")

    @classmethod
    def from_result(cls, r: SeriesRecommendations) -> SeriesRecommendationsResponse:
        return cls(
            hsk_level=r.hsk_level,
            needs_level=r.hsk_level is None,
            items=[RecommendedSeriesResponse.from_recommendation(i) for i in r.items],
        )


class ChapterCoverageResponse(BaseModel):
    hsk_level: int | None = Field(description="Trình độ n; null: tính trên mọi từ có cấp HSK")
    needs_level: bool
    known_terms: int = Field(description="X: số từ đã có trong sổ tay (mọi trạng thái)")
    total_terms: int = Field(description="Y: số từ khác nhau trong chương có cấp HSK 1..n")
    percent: int = Field(description="X/Y làm tròn, 0..100")
    status: str = Field(
        description="ready | processing (còn trang chưa xong, tạm tính) | empty (không có từ)"
    )

    @classmethod
    def from_coverage(cls, c: ChapterCoverage) -> ChapterCoverageResponse:
        return cls(
            hsk_level=c.hsk_level,
            needs_level=c.hsk_level is None,
            known_terms=c.known_terms,
            total_terms=c.total_terms,
            percent=c.percent,
            status=c.status,
        )
