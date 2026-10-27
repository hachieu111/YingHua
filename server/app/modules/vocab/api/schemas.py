from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.uploads import file_url
from app.modules.review.application.public import Card, EntrySrsSummary
from app.modules.vocab.application.dto import (
    ContextSource,
    ContextView,
    DeckList,
    DeckSummary,
    SaveWordResult,
    VocabDetail,
    VocabListItem,
    VocabListPage,
)
from app.modules.vocab.domain.entities import VocabContext, VocabEntry
from app.modules.vocab.domain.rules import MAX_TERM_CHARS


class SaveWordRequest(BaseModel):
    term: str = Field(
        min_length=1, max_length=64, description=f"Từ tiếng Trung, tối đa {MAX_TERM_CHARS} ký tự"
    )
    source: str = Field(
        default="highlight",
        max_length=12,
        description="highlight (khung Hover) | lookup (tra cứu) | suggestion | manual | quiz",
    )
    bubble_id: int | None = Field(
        default=None, ge=1, description="Bong bóng chứa từ (khi lưu lúc đọc truyện)"
    )
    page_id: int | None = Field(default=None, ge=1, description="Trang đang đọc; bỏ trống thì máy chủ tự tìm")
    meaning_vi: str | None = Field(default=None, max_length=1000, description="Nghĩa tự nhập (nguồn manual)")


class UpdateVocabRequest(BaseModel):
    """Chỉ các trường có trong thân yêu cầu được đổi."""

    status: str | None = Field(default=None, max_length=12, description="learning | known | ignored")
    note: str | None = Field(
        default=None, max_length=2000, description="Ghi chú ≤ 1000 ký tự; rỗng/null = xóa"
    )
    meaning_vi: str | None = Field(default=None, max_length=2000)
    is_starred: bool | None = None


class ContextBriefResponse(BaseModel):
    id: int
    snippet_url: str | None
    sentence_zh: str
    sentence_vi: str | None
    source_label: str | None

    @classmethod
    def from_context(cls, c: VocabContext) -> ContextBriefResponse:
        return cls(
            id=c.id,
            snippet_url=file_url(c.snippet_file_id),
            sentence_zh=c.sentence_zh,
            sentence_vi=c.sentence_vi,
            source_label=c.source_label,
        )


class ContextSourceResponse(BaseModel):
    series_id: int | None
    series_title: str | None
    chapter_id: int | None
    chapter_number: float | None
    page_id: int
    page_no: int

    @classmethod
    def from_source(cls, s: ContextSource) -> ContextSourceResponse:
        return cls(
            series_id=s.series_id,
            series_title=s.series_title,
            chapter_id=s.chapter_id,
            chapter_number=float(s.chapter_number) if s.chapter_number is not None else None,
            page_id=s.page_id,
            page_no=s.page_no,
        )


class VocabContextResponse(BaseModel):
    id: int
    bubble_id: int | None
    page_id: int | None
    snippet_url: str | None
    sentence_zh: str
    sentence_vi: str | None
    source_label: str | None
    source: ContextSourceResponse | None = Field(
        description="Nguồn để mở lại trang truyện; null khi trang đã xóa hoặc hết quyền đọc"
    )
    created_at: datetime

    @classmethod
    def from_view(cls, v: ContextView) -> VocabContextResponse:
        c = v.context
        return cls(
            id=c.id,
            bubble_id=c.bubble_id,
            page_id=c.page_id,
            snippet_url=file_url(c.snippet_file_id),
            sentence_zh=c.sentence_zh,
            sentence_vi=c.sentence_vi,
            source_label=c.source_label,
            source=ContextSourceResponse.from_source(v.source) if v.source else None,
            created_at=c.created_at,
        )


class SrsSummaryResponse(BaseModel):
    card_count: int
    due_count: int = Field(description="Số thẻ đang đến hạn (chưa xét trạng thái học của từ)")
    review_count: int = Field(description="Tổng số lượt ôn đã chấm của các thẻ")
    next_due_at: datetime | None

    @classmethod
    def from_summary(cls, s: EntrySrsSummary) -> SrsSummaryResponse:
        return cls(
            card_count=s.card_count,
            due_count=s.due_count,
            review_count=s.review_count,
            next_due_at=s.next_due_at,
        )


class CardBriefResponse(BaseModel):
    id: int
    card_type: str
    state: str
    due_at: datetime
    last_review_at: datetime | None
    is_suspended: bool
    reps: int
    lapses: int

    @classmethod
    def from_card(cls, c: Card) -> CardBriefResponse:
        return cls(
            id=c.id,
            card_type=c.card_type.value,
            state=c.schedule.state.value,
            due_at=c.schedule.due_at,
            last_review_at=c.schedule.last_review_at,
            is_suspended=c.is_suspended,
            reps=c.reps,
            lapses=c.lapses,
        )


class VocabEntryBase(BaseModel):
    id: int
    term: str
    pinyin: str | None
    meaning_vi: str | None
    sino_vietnamese: str | None = Field(description="Âm Hán Việt ghép từ từ điển; null nếu thiếu dữ liệu")
    hsk_level: int | None = Field(description="null = Ngoài HSK")
    hsk_source: str = Field(description="list | derived (suy từ chữ cấu thành) | none")
    status: str = Field(description="learning | known | ignored")
    source: str
    note: str | None
    is_starred: bool
    is_due: bool = Field(description='Có thẻ đến hạn và từ còn "Đang học"')
    srs: SrsSummaryResponse | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def base_fields(
        e: VocabEntry, sino: str | None, srs: EntrySrsSummary | None, is_due: bool
    ) -> dict[str, Any]:
        return {
            "id": e.id,
            "term": e.term,
            "pinyin": e.pinyin,
            "meaning_vi": e.meaning_vi,
            "sino_vietnamese": sino,
            "hsk_level": e.hsk_level,
            "hsk_source": e.hsk_source,
            "status": e.status.value,
            "source": e.origin.value,
            "note": e.note,
            "is_starred": e.is_starred,
            "is_due": is_due,
            "srs": SrsSummaryResponse.from_summary(srs) if srs else None,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
        }


class VocabEntryItemResponse(VocabEntryBase):
    contexts_count: int
    first_context: ContextBriefResponse | None

    @classmethod
    def from_item(cls, i: VocabListItem) -> VocabEntryItemResponse:
        return cls(
            **cls.base_fields(i.entry, i.sino_vietnamese, i.srs, i.is_due),
            contexts_count=i.contexts_count,
            first_context=ContextBriefResponse.from_context(i.first_context) if i.first_context else None,
        )


class VocabEntryDetailResponse(VocabEntryBase):
    contexts_count: int
    contexts: list[VocabContextResponse]
    cards: list[CardBriefResponse]

    @classmethod
    def from_detail(cls, d: VocabDetail) -> VocabEntryDetailResponse:
        return cls(
            **cls.base_fields(d.entry, d.sino_vietnamese, d.srs, d.is_due),
            contexts_count=len(d.contexts),
            contexts=[VocabContextResponse.from_view(v) for v in d.contexts],
            cards=[CardBriefResponse.from_card(c) for c in d.cards],
        )


class SaveWordResponse(BaseModel):
    entry: VocabEntryDetailResponse
    created: bool = Field(description="true: mục từ mới (kèm 3 thẻ). false: từ đã có, chỉ thêm ngữ cảnh")
    context_added: bool
    cards_created: int
    snippet_missing: bool = Field(
        description="Có bong bóng nhưng không cắt được ảnh; đã lưu câu văn thay thế"
    )

    @classmethod
    def from_result(cls, r: SaveWordResult) -> SaveWordResponse:
        return cls(
            entry=VocabEntryDetailResponse.from_detail(r.detail),
            created=r.created,
            context_added=r.context is not None,
            cards_created=len(r.cards),
            snippet_missing=r.snippet_missing,
        )


class VocabPageResponse(BaseModel):
    items: list[VocabEntryItemResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, p: VocabListPage, page: int, size: int) -> VocabPageResponse:
        return cls(
            items=[VocabEntryItemResponse.from_item(i) for i in p.items], total=p.total, page=page, size=size
        )


class DeckResponse(BaseModel):
    key: str = Field(description="Dùng làm tham số `deck` của GET /cards/due: starred | series:<id>")
    kind: str = Field(description="starred | series")
    series_id: int | None
    title: str
    word_count: int
    reviewed_count: int = Field(description="Số từ đã ôn ít nhất một lượt")
    due_count: int = Field(description="Số thẻ đang đến hạn")

    @classmethod
    def from_deck(cls, d: DeckSummary) -> DeckResponse:
        return cls(**{f: getattr(d, f) for f in cls.model_fields})


class DeckListResponse(BaseModel):
    items: list[DeckResponse]
    generated_at: datetime

    @classmethod
    def from_list(cls, d: DeckList) -> DeckListResponse:
        return cls(items=[DeckResponse.from_deck(i) for i in d.items], generated_at=d.generated_at)


class SavedStatusResponse(BaseModel):
    terms: list[str] = Field(description="Các từ trong yêu cầu đã có trong sổ tay")
    page_terms: list[str] = Field(description="Các từ đã có ngữ cảnh từ trang `page_id` (đã lưu ở trang này)")
    bubble_ids: list[int] = Field(description="Các bong bóng trong yêu cầu đã lưu câu thoại")
