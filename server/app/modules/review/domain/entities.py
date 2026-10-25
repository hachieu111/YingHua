"""Thực thể của M08 Ôn tập — thuần Python, không phụ thuộc framework hay thư viện FSRS."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum


class CardType(str, Enum):
    """Ba loại thẻ của mỗi từ (F08.03)."""

    RECOGNITION = "recognition"  # Hán -> Việt
    RECALL = "recall"  # Việt -> Hán
    LISTENING = "listening"  # âm thanh -> Hán


class CardState(str, Enum):
    """Đúng ba trạng thái của FSRS."""

    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class Rating(IntEnum):
    """Bốn mức tự đánh giá Quên/Khó/Được/Dễ (F08.02)."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True, slots=True)
class SchedulingState:
    """Trạng thái lập lịch của một thẻ (S, D, bước học, hạn ôn) — đầu vào và đầu ra của bộ lập lịch."""

    state: CardState
    step: int | None
    stability: float | None
    difficulty: float | None
    due_at: datetime
    last_review_at: datetime | None


@dataclass(slots=True)
class Card:
    id: int
    user_id: int
    vocab_entry_id: int
    card_type: CardType
    schedule: SchedulingState
    reps: int
    lapses: int
    is_suspended: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CardFilter:
    """Bộ lọc danh sách thẻ của một người học (F13.07). `due` theo quy tắc thẻ đến hạn của F08.01."""

    user_id: int
    now: datetime
    state: CardState | None = None
    suspended: bool | None = None
    due: bool | None = None


@dataclass(frozen=True, slots=True)
class NewCard:
    user_id: int
    vocab_entry_id: int
    card_type: CardType
    schedule: SchedulingState
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewLog:
    id: int
    card_id: int
    user_id: int
    rating: Rating
    state_before: CardState
    stability_before: float | None
    stability_after: float | None
    difficulty_before: float | None
    difficulty_after: float | None
    due_after: datetime
    duration_ms: int | None
    presentation_id: uuid.UUID
    reviewed_at: datetime


@dataclass(frozen=True, slots=True)
class NewReviewLog:
    card_id: int
    user_id: int
    rating: Rating
    state_before: CardState
    stability_before: float | None
    stability_after: float | None
    difficulty_before: float | None
    difficulty_after: float | None
    due_after: datetime
    duration_ms: int | None
    presentation_id: uuid.UUID
    reviewed_at: datetime


class DeckKind(str, Enum):
    ALL = "all"
    STARRED = "starred"
    SERIES = "series"


@dataclass(frozen=True, slots=True)
class DeckRef:
    """Bộ thẻ: toàn bộ, "Từ đánh dấu sao" hoặc theo truyện. Khóa văn bản: `all`, `starred`, `series:<id>`."""

    kind: DeckKind
    series_id: int | None = None

    @property
    def key(self) -> str:
        return f"series:{self.series_id}" if self.kind is DeckKind.SERIES else self.kind.value


@dataclass(frozen=True, slots=True)
class EntrySrsSummary:
    """Tóm tắt thẻ của một mục từ (dùng cho danh sách sổ tay và bộ thẻ)."""

    vocab_entry_id: int
    card_count: int
    due_count: int
    review_count: int  # tổng số lượt ôn đã chấm của các thẻ
    next_due_at: datetime | None
