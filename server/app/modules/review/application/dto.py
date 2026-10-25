from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.modules.review.domain.ai_note import AiNote, CharParts
from app.modules.review.domain.entities import Card, DeckRef, Rating, ReviewLog


@dataclass(frozen=True, slots=True)
class ContextFace:
    """Ngữ cảnh hiển thị trên mặt sau của thẻ (F08.04): ảnh bong bóng đã cắt và câu văn."""

    context_id: int
    snippet_file_id: int | None
    sentence_zh: str
    sentence_vi: str | None
    source_label: str | None


@dataclass(frozen=True, slots=True)
class EntryFace:
    """Nội dung của mục từ cần cho hai mặt thẻ (F08.03); do M07 cung cấp."""

    vocab_entry_id: int
    term: str
    pinyin: str | None
    meaning_vi: str | None
    sino_vietnamese: str | None
    note: str | None
    status: str
    is_starred: bool
    hsk_level: int | None
    context: ContextFace | None  # ngữ cảnh mới nhất
    contexts_count: int = 0


@dataclass(frozen=True, slots=True)
class DueCard:
    card: Card
    face: EntryFace


@dataclass(frozen=True, slots=True)
class DueBatch:
    total: int
    cards: list[DueCard]
    deck: DeckRef


@dataclass(frozen=True, slots=True)
class GradeCommand:
    card_id: int
    rating: int
    presentation_id: uuid.UUID
    duration_ms: int | None = None
    deck: str | None = None  # bộ thẻ để chọn thẻ kế tiếp


@dataclass(frozen=True, slots=True)
class GradeResult:
    card: Card
    rating: Rating
    reviewed_at: datetime
    due_at: datetime
    interval_seconds: int
    duplicate: bool
    next_batch: DueBatch


@dataclass(frozen=True, slots=True)
class HistoryPage:
    card: Card
    items: list[ReviewLog]
    total: int


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    """F08.07: status là `no_cards`, `due` (còn thẻ đến hạn) hoặc `completed` (đã ôn xong)."""

    status: str
    reviewed_today: int
    due_now: int
    due_later_today: int
    next_due_at: datetime | None
    total_cards: int
    timezone: str
    due_words: int
    status_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class ListCardsQuery:
    state: str | None = None
    suspended: bool | None = None
    due: bool | None = None
    page: int = 1
    size: int = 20


@dataclass(frozen=True, slots=True)
class CardListItem:
    card: Card
    face: EntryFace | None  # None nếu mục từ vừa bị xóa đồng thời


@dataclass(frozen=True, slots=True)
class CardListPage:
    items: list[CardListItem]
    total: int


@dataclass(frozen=True, slots=True)
class AiNoteRequest:
    """Dữ liệu gửi LLM cho Thẻ mở rộng (F08.11): chỉ từ, pinyin, nghĩa ngắn, cấp HSK, trình độ (một con số)
    và dữ liệu phân rã chữ Hán của từ điển; tuyệt đối không có thông tin người học (security.md)."""

    term: str
    pinyin: str | None
    meaning: str | None
    hsk_level: int | None
    learner_level: int | None
    parts: tuple[CharParts, ...] = ()


@dataclass(frozen=True, slots=True)
class AiNoteView:
    note: AiNote
    regenerate_limit: int

    @property
    def regenerate_remaining(self) -> int:
        return max(self.regenerate_limit - self.note.regenerate_count, 0)
