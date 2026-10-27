from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.modules.library.application.public import PageAccess
from app.modules.review.application.public import Card, EntrySrsSummary
from app.modules.vocab.domain.entities import SavedSentence, VocabContext, VocabEntry


@dataclass(frozen=True, slots=True)
class SaveWordCommand:
    """Yêu cầu lưu từ (F07.01). `bubble_id` có khi lưu từ khung Hover; `page_id` là trang đang đọc."""

    term: str
    source: str
    bubble_id: int | None = None
    page_id: int | None = None
    meaning_vi: str | None = None


@dataclass(frozen=True, slots=True)
class SaveWordResult:
    detail: VocabDetail
    created: bool  # True: mục từ mới (kèm 3 thẻ); False: mục từ đã có
    context: VocabContext | None  # ngữ cảnh vừa thêm
    snippet_missing: bool  # có bong bóng nhưng không cắt được ảnh (vẫn lưu câu văn)
    cards: list[Card] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ListVocabQuery:
    status: str | None = None
    hsk: str | None = None
    query: str | None = None
    starred: bool | None = None
    series_id: int | None = None
    due: bool | None = None
    page: int = 1
    size: int = 20


@dataclass(frozen=True, slots=True)
class VocabListItem:
    entry: VocabEntry
    sino_vietnamese: str | None
    contexts_count: int
    first_context: VocabContext | None
    srs: EntrySrsSummary | None

    @property
    def is_due(self) -> bool:
        """Có thẻ đến hạn và từ còn "Đang học" (từ đã thuộc/bỏ qua không tham gia lịch ôn)."""
        return self.entry.status.value == "learning" and self.srs is not None and self.srs.due_count > 0


@dataclass(frozen=True, slots=True)
class VocabListPage:
    items: list[VocabListItem]
    total: int


@dataclass(frozen=True, slots=True)
class ContextSource:
    """Nguồn của ngữ cảnh (truyện, chương, trang) để mở lại trang gốc (F07.05)."""

    series_id: int | None
    series_title: str | None
    chapter_id: int | None
    chapter_number: Decimal | None
    page_id: int
    page_no: int


@dataclass(frozen=True, slots=True)
class ContextView:
    context: VocabContext
    source: ContextSource | None  # None: trang không còn hoặc người gọi hết quyền đọc


@dataclass(frozen=True, slots=True)
class VocabDetail:
    entry: VocabEntry
    sino_vietnamese: str | None
    contexts: list[ContextView]
    cards: list[Card]
    srs: EntrySrsSummary | None

    @property
    def is_due(self) -> bool:
        return self.entry.status.value == "learning" and self.srs is not None and self.srs.due_count > 0


@dataclass(frozen=True, slots=True)
class DeckSummary:
    key: str  # starred | series:<id>
    kind: str  # starred | series
    series_id: int | None
    title: str
    word_count: int
    reviewed_count: int  # số từ đã được ôn ít nhất một lượt
    due_count: int  # số thẻ đang đến hạn của các từ còn "Đang học"


@dataclass(frozen=True, slots=True)
class DeckList:
    items: list[DeckSummary]
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class SaveSentenceCommand:
    """Yêu cầu lưu câu thoại (F07.11). `page_id` là trang đang đọc; bỏ trống thì máy chủ tự tìm."""

    bubble_id: int
    note: str | None = None
    page_id: int | None = None


@dataclass(frozen=True, slots=True)
class SavedSentenceItem:
    sentence: SavedSentence
    pinyin: str | None  # ghép từ dữ liệu tách từ nếu bong bóng gốc còn
    page: PageAccess | None  # trang gốc còn đọc được; None thì giao diện ẩn nút "Mở trang gốc"


@dataclass(frozen=True, slots=True)
class SavedSentencePage:
    items: list[SavedSentenceItem]
    total: int


@dataclass(frozen=True, slots=True)
class FailedWord:
    term: str
    code: str


@dataclass(frozen=True, slots=True)
class SaveAllWordsResult:
    """Kết quả lưu hàng loạt từ của một trang (F07.12)."""

    saved: list[str]
    existing: list[str]
    failed: list[FailedWord]
    remaining: int  # số từ còn lại chưa lưu vì quá giới hạn mỗi lần
    skipped: list[str] = field(default_factory=list)  # từ một chữ rất phổ biến (是, 吗…): không tự lưu


@dataclass(frozen=True, slots=True)
class SavedStatus:
    """Từ đã có trong sổ tay và câu thoại đã lưu — để giao diện hiện đúng dấu "đã lưu" sau khi tải lại."""

    terms: list[str]  # đã có trong sổ tay (ở bất kỳ ngữ cảnh nào)
    page_terms: list[str]  # đã có ngữ cảnh lấy từ trang đang xem
    bubble_ids: list[int]
