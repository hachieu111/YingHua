"""Thực thể của M10 Gợi ý từ — thuần Python. Danh sách gợi ý tính khi yêu cầu, không lưu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BubbleTokens:
    """Từ đã tách của một bong bóng, kèm vị trí trong chương."""

    page_id: int
    page_no: int
    bubble_id: int
    idx: int
    tokens: list[Any]


@dataclass(slots=True)
class TermStats:
    """Thống kê một từ trong chương: số lần xuất hiện và lần xuất hiện đầu tiên (làm ngữ cảnh, F10.02)."""

    term: str
    occurrences: int
    page_id: int
    page_no: int
    bubble_id: int
    pinyin: str | None = None


@dataclass(frozen=True, slots=True)
class ScoredTerm:
    stats: TermStats
    lookups: int
    hsk_level: int | None
    score: float


@dataclass(frozen=True, slots=True)
class Suggestion:
    term: str
    pinyin: str | None
    meaning_vi: str | None
    hsk_level: int | None
    occurrences: int
    lookups: int
    score: float
    bubble_id: int
    page_id: int
    page_no: int


@dataclass(frozen=True, slots=True)
class DismissedTerm:
    term: str
    dismissed_at: datetime


@dataclass(frozen=True, slots=True)
class SeriesCandidate:
    """Truyện công khai ứng viên để gợi ý theo trình độ (F10.04)."""

    series_id: int
    title_vi: str
    title_zh: str | None
    cover_file_id: int | None
    est_hsk_level: int | None
    genres: tuple[str, ...]
    rating_avg: float | None
    rating_count: int
    chapter_count: int
    library_count: int  # số người đã thêm vào Thư viện cá nhân: độ phổ biến
    in_library: bool
    finished: bool


@dataclass(frozen=True, slots=True)
class SeriesRecommendation:
    candidate: SeriesCandidate
    reason: str
