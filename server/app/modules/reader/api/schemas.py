from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.uploads import file_url
from app.modules.dictionary.api.public import LookupResponse
from app.modules.reader.application.dto import (
    BookmarkPage,
    BubbleLookup,
    EditedBubble,
    ReadingBubble,
    ReadingView,
)
from app.modules.reader.domain.entities import Annotation, AnnotationInput, Stroke
from app.modules.reader.domain.rules import MAX_EDIT_CHARS, percent


class SaveBubbleEditRequest(BaseModel):
    text_vi: str = Field(min_length=1, max_length=MAX_EDIT_CHARS, description="Bản dịch riêng, 1..1000 ký tự")


class SetBookmarkRequest(BaseModel):
    is_bookmarked: bool


class PointSchema(BaseModel):
    x: float
    y: float


class StrokeSchema(BaseModel):
    color: str = Field(max_length=7, description="Màu #rrggbb")
    points: list[PointSchema]


class SaveAnnotationsRequest(BaseModel):
    highlights: dict[int, str] = Field(
        default_factory=dict, description="Mã bong bóng → màu #rrggbb (chỉ các bong bóng được tô)"
    )
    strokes: list[StrokeSchema] = Field(
        default_factory=list, description="Nét vẽ tự do: màu + danh sách điểm"
    )

    def to_input(self) -> AnnotationInput:
        return AnnotationInput(
            highlights=dict(self.highlights),
            strokes=tuple(Stroke(s.color, tuple((p.x, p.y) for p in s.points)) for s in self.strokes),
        )


class AnnotationResponse(BaseModel):
    is_bookmarked: bool
    highlights: dict[int, str]
    strokes: list[StrokeSchema]
    updated_at: datetime

    @classmethod
    def from_entity(cls, a: Annotation) -> AnnotationResponse:
        return cls(
            is_bookmarked=a.is_bookmarked,
            highlights=a.highlights,
            strokes=[
                StrokeSchema(color=s.color, points=[PointSchema(x=x, y=y) for x, y in s.points])
                for s in a.strokes
            ],
            updated_at=a.updated_at,
        )


class TokenResponse(BaseModel):
    word: str
    pinyin: str | None = None
    entry_id: int | None = None


def _token(raw: Any) -> TokenResponse | None:
    if not isinstance(raw, dict):
        return None
    word = raw.get("word") or raw.get("text")
    if not isinstance(word, str) or not word:
        return None
    entry_id = raw.get("entry_id")
    return TokenResponse(
        word=word,
        pinyin=raw.get("pinyin") if isinstance(raw.get("pinyin"), str) else None,
        entry_id=entry_id if isinstance(entry_id, int) else None,
    )


class ReadingBubbleResponse(BaseModel):
    id: int
    idx: int
    class_name: str
    x: int
    y: int
    w: int
    h: int
    x_pct: float | None
    y_pct: float | None
    w_pct: float | None
    h_pct: float | None
    polygon: Any | None
    confidence: float | None
    text_zh: str
    pinyin: str | None
    text_vi: str | None = Field(description="Bản dịch dùng chung")
    text_vi_effective: str | None = Field(description="Bản sửa riêng của người gọi nếu có, không thì text_vi")
    has_edit: bool
    tokens: list[TokenResponse]
    lines: list[Any]
    style: Any | None
    translate_method: str | None

    @classmethod
    def from_item(cls, item: ReadingBubble, width: int | None, height: int | None) -> ReadingBubbleResponse:
        b = item.bubble
        return cls(
            id=b.id,
            idx=b.idx,
            class_name=b.class_name,
            x=b.x,
            y=b.y,
            w=b.w,
            h=b.h,
            x_pct=percent(b.x, width),
            y_pct=percent(b.y, height),
            w_pct=percent(b.w, width),
            h_pct=percent(b.h, height),
            polygon=b.polygon,
            confidence=b.confidence,
            text_zh=b.text_zh,
            pinyin=b.pinyin,
            text_vi=b.text_vi,
            text_vi_effective=item.text_vi_effective,
            has_edit=item.edited_text is not None,
            tokens=[t for t in (_token(r) for r in b.tokens) if t is not None],
            lines=list(b.lines),
            style=b.style,
            translate_method=b.translate_method,
        )


class ReadingPageInfo(BaseModel):
    id: int
    page_no: int
    chapter_id: int | None
    series_id: int | None
    width: int | None
    height: int | None
    status: str | None
    text_ready: bool = Field(
        description="Chữ và bản dịch đã sẵn sàng (đã `done` hoặc đã có bong bóng dù còn running/failed)"
    )
    error_step: str | None
    error_message: str | None
    can_edit: bool


class ReadingVariants(BaseModel):
    original: str | None
    inpainted: str | None
    rendered: str | None


class ReadingResponse(BaseModel):
    page: ReadingPageInfo
    variants: ReadingVariants
    bubbles: list[ReadingBubbleResponse]
    annotation: AnnotationResponse | None = Field(
        description="Ghi chú và dấu trang của người gọi; null với Khách"
    )

    @classmethod
    def from_view(cls, v: ReadingView) -> ReadingResponse:
        a, t = v.access, v.translation
        return cls(
            page=ReadingPageInfo(
                id=a.page_id,
                page_no=a.page_no,
                chapter_id=a.chapter_id,
                series_id=a.series_id,
                width=a.width,
                height=a.height,
                status=t.status.value if t else None,
                text_ready=t.text_ready if t else False,
                error_step=t.error_step if t else None,
                error_message=t.error_message if t else None,
                can_edit=a.can_edit,
            ),
            variants=ReadingVariants(
                original=file_url(a.original_file_id),
                inpainted=file_url(t.inpainted_file_id) if t else None,
                rendered=file_url(t.rendered_file_id) if t else None,
            ),
            bubbles=[ReadingBubbleResponse.from_item(b, a.width, a.height) for b in v.bubbles],
            annotation=AnnotationResponse.from_entity(v.annotation) if v.annotation else None,
        )


class GuestQuotaResponse(BaseModel):
    session_id: str
    limit: int
    used: int
    remaining: int


class BubbleLookupResponse(BaseModel):
    bubble_id: int
    word: str
    lookup: LookupResponse
    guest: GuestQuotaResponse | None = Field(
        description="Hạn mức tra thử của Khách; null với người đã đăng nhập"
    )

    @classmethod
    def from_lookup(cls, r: BubbleLookup) -> BubbleLookupResponse:
        g = r.guest
        return cls(
            bubble_id=r.bubble_id,
            word=r.word,
            lookup=LookupResponse.from_result(r.result),
            guest=GuestQuotaResponse(
                session_id=g.session_id, limit=g.limit, used=g.used, remaining=g.remaining
            )
            if g
            else None,
        )


class BubbleEditResponse(BaseModel):
    bubble_id: int
    text_vi: str | None
    text_vi_effective: str | None
    has_edit: bool

    @classmethod
    def from_edited(cls, e: EditedBubble) -> BubbleEditResponse:
        return cls(
            bubble_id=e.bubble.id,
            text_vi=e.bubble.text_vi,
            text_vi_effective=e.text_vi_effective,
            has_edit=e.edited_text is not None,
        )


class BookmarkResponse(BaseModel):
    page_id: int
    is_bookmarked: bool


class BookmarkItemResponse(BaseModel):
    page_id: int
    page_no: int
    chapter_id: int | None
    chapter_number: float | None
    series_id: int | None
    series_title: str | None
    original_url: str | None
    bookmarked_at: datetime


class BookmarkPageResponse(BaseModel):
    items: list[BookmarkItemResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, result: BookmarkPage, page: int, size: int) -> BookmarkPageResponse:
        return cls(
            items=[
                BookmarkItemResponse(
                    page_id=i.access.page_id,
                    page_no=i.access.page_no,
                    chapter_id=i.access.chapter_id,
                    chapter_number=float(i.access.chapter_number)
                    if i.access.chapter_number is not None
                    else None,
                    series_id=i.access.series_id,
                    series_title=i.access.series_title,
                    original_url=file_url(i.access.original_file_id),
                    bookmarked_at=i.bookmarked_at,
                )
                for i in result.items
            ],
            total=result.total,
            page=page,
            size=size,
        )
