from __future__ import annotations

from dataclasses import dataclass

from app.modules.suggestions.domain.entities import DismissedTerm, SeriesRecommendation, Suggestion


@dataclass(frozen=True, slots=True)
class SuggestionList:
    status: str  # ready | processing
    hsk_level: int | None  # trình độ đã khai báo; None để giao diện nhắc khai báo (US-NH-51 TC3)
    items: list[Suggestion]


@dataclass(frozen=True, slots=True)
class DismissedItem:
    dismissed: DismissedTerm
    pinyin: str | None
    meaning_vi: str | None
    hsk_level: int | None


@dataclass(frozen=True, slots=True)
class DismissedPage:
    items: list[DismissedItem]
    total: int


@dataclass(frozen=True, slots=True)
class SeriesRecommendations:
    hsk_level: int | None
    items: list[SeriesRecommendation]


@dataclass(frozen=True, slots=True)
class ChapterCoverage:
    hsk_level: int | None  # trình độ đã khai báo; None: đang tính trên mọi từ có cấp HSK
    known_terms: int
    total_terms: int
    percent: int
    status: str  # ready | processing | empty
