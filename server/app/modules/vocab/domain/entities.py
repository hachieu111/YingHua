"""Thực thể của M07 Sổ tay — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class VocabStatus(str, Enum):
    """Trạng thái học (F07.03): "Đã thuộc" và "Bỏ qua" loại thẻ khỏi danh sách đến hạn."""

    LEARNING = "learning"
    KNOWN = "known"
    IGNORED = "ignored"


class VocabOrigin(str, Enum):
    """Nơi từ được lưu từ đâu."""

    HIGHLIGHT = "highlight"  # bấm Lưu trên khung Hover khi đọc
    LOOKUP = "lookup"  # từ trang tra cứu
    SUGGESTION = "suggestion"  # từ gợi ý
    MANUAL = "manual"
    QUIZ = "quiz"


@dataclass(slots=True)
class VocabEntry:
    id: int
    user_id: int
    term: str
    status: VocabStatus
    origin: VocabOrigin
    hsk_source: str  # list | derived | none
    created_at: datetime
    updated_at: datetime
    entry_id: int | None = None  # mục từ điển M06
    pinyin: str | None = None
    meaning_vi: str | None = None
    hsk_level: int | None = None
    note: str | None = None
    is_starred: bool = False


@dataclass(frozen=True, slots=True)
class NewVocabEntry:
    user_id: int
    term: str
    origin: VocabOrigin
    hsk_source: str
    created_at: datetime
    entry_id: int | None = None
    pinyin: str | None = None
    meaning_vi: str | None = None
    hsk_level: int | None = None


@dataclass(slots=True)
class VocabContext:
    id: int
    vocab_entry_id: int
    sentence_zh: str
    created_at: datetime
    bubble_id: int | None = None
    page_id: int | None = None
    sentence_vi: str | None = None
    snippet_file_id: int | None = None
    source_label: str | None = None


@dataclass(frozen=True, slots=True)
class NewVocabContext:
    vocab_entry_id: int
    sentence_zh: str
    created_at: datetime
    bubble_id: int | None = None
    page_id: int | None = None
    sentence_vi: str | None = None
    snippet_file_id: int | None = None
    source_label: str | None = None


@dataclass(frozen=True, slots=True)
class ContextSummary:
    """Số ngữ cảnh và ngữ cảnh mới nhất của một mục từ (danh sách sổ tay, mặt sau thẻ)."""

    count: int
    latest: VocabContext | None


@dataclass(frozen=True, slots=True)
class VocabFilter:
    """Điều kiện lọc sổ tay (F07.07); các điều kiện ghép bằng "và"."""

    user_id: int
    status: VocabStatus | None = None
    hsk_level: int | None = None
    hsk_none: bool = False  # "Ngoài HSK"
    query: str | None = None
    starred: bool | None = None
    page_ids: Sequence[int] | None = None  # trang thuộc truyện đang lọc; rỗng nghĩa là không có kết quả
    due: bool | None = None  # True: có thẻ đến hạn; False: không có (cần `now`)
    now: datetime | None = None  # mốc "đến hạn" khi lọc `due`


@dataclass(frozen=True, slots=True)
class CropBox:
    left: int
    top: int
    right: int
    bottom: int


@dataclass(slots=True)
class SavedSentence:
    """Câu thoại đã lưu (F07.11): bản sao văn bản của một bong bóng tại thời điểm lưu."""

    id: int
    user_id: int
    sentence_zh: str
    created_at: datetime
    updated_at: datetime
    bubble_id: int | None = None  # None khi bong bóng gốc đã bị xóa
    page_id: int | None = None  # None khi trang gốc đã bị xóa
    sentence_vi: str | None = None
    source_label: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class NewSavedSentence:
    user_id: int
    sentence_zh: str
    created_at: datetime
    bubble_id: int | None = None
    page_id: int | None = None
    sentence_vi: str | None = None
    source_label: str | None = None
    note: str | None = None
