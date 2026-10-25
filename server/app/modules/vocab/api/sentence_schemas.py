"""Schema API của câu thoại đã lưu (F07.11) và lưu tất cả từ của trang (F07.12)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.vocab.application.dto import (
    FailedWord,
    SaveAllWordsResult,
    SavedSentenceItem,
    SavedSentencePage,
)


class SaveSentenceRequest(BaseModel):
    bubble_id: int = Field(ge=1, description="Bong bóng (câu thoại) cần lưu")
    note: str | None = Field(default=None, max_length=2000, description="Ghi chú ≤ 1000 ký tự")
    page_id: int | None = Field(default=None, ge=1, description="Trang đang đọc; bỏ trống thì máy chủ tự tìm")


class UpdateSentenceNoteRequest(BaseModel):
    note: str | None = Field(
        default=None, max_length=2000, description="Ghi chú ≤ 1000 ký tự; rỗng/null = xóa"
    )


class SavedSentenceResponse(BaseModel):
    id: int
    sentence_zh: str
    sentence_vi: str | None
    pinyin: str | None = Field(description="Ghép từ dữ liệu tách từ; null nếu bong bóng gốc đã bị xóa")
    source_label: str | None = Field(description='"Truyện · Chương · Trang"')
    bubble_id: int | None
    page_id: int | None = Field(description="null khi trang gốc đã xóa hoặc không còn đọc được: ẩn nút mở")
    chapter_id: int | None
    page_no: int | None
    note: str | None
    created_at: datetime

    @classmethod
    def from_item(cls, item: SavedSentenceItem) -> SavedSentenceResponse:
        s, page = item.sentence, item.page
        return cls(
            id=s.id,
            sentence_zh=s.sentence_zh,
            sentence_vi=s.sentence_vi,
            pinyin=item.pinyin,
            source_label=s.source_label,
            bubble_id=s.bubble_id,
            page_id=page.page_id if page else None,
            chapter_id=page.chapter_id if page else None,
            page_no=page.page_no if page else None,
            note=s.note,
            created_at=s.created_at,
        )


class SavedSentencePageResponse(BaseModel):
    items: list[SavedSentenceResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, p: SavedSentencePage, page: int, size: int) -> SavedSentencePageResponse:
        return cls(
            items=[SavedSentenceResponse.from_item(i) for i in p.items], total=p.total, page=page, size=size
        )


class FailedWordResponse(BaseModel):
    term: str
    code: str = Field(description="Mã lỗi nghiệp vụ, vd. TERM_NOT_IN_BUBBLE")

    @classmethod
    def from_failed(cls, f: FailedWord) -> FailedWordResponse:
        return cls(term=f.term, code=f.code)


class SaveAllWordsResponse(BaseModel):
    saved: list[str] = Field(description="Từ mới lưu (kèm ngữ cảnh và 3 thẻ)")
    existing: list[str] = Field(description="Từ đã có trong sổ tay từ trước")
    failed: list[FailedWordResponse]
    remaining: int = Field(description="Số từ còn lại chưa lưu vì quá 50 từ mỗi lần; bấm lưu tiếp để lưu nốt")
    skipped: list[str] = Field(
        default_factory=list, description="Từ một chữ rất phổ biến (是, 吗…), không tự lưu"
    )

    @classmethod
    def from_result(cls, r: SaveAllWordsResult) -> SaveAllWordsResponse:
        return cls(
            saved=r.saved,
            existing=r.existing,
            failed=[FailedWordResponse.from_failed(f) for f in r.failed],
            remaining=r.remaining,
            skipped=r.skipped,
        )
