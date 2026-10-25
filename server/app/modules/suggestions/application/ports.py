"""Giao diện (port) mà tầng hạ tầng của M10 phải hiện thực."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.modules.auth.application.public import Identity
from app.modules.imaging.application.public import BubbleRepository
from app.modules.suggestions.domain.entities import DismissedTerm, SeriesCandidate
from app.modules.vocab.application.public import SaveWordCommand, SaveWordResult


@dataclass(frozen=True, slots=True)
class ChapterPage:
    page_id: int
    page_no: int
    translation_id: int | None
    translation_status: str | None  # queued | running | done | failed; None: chưa có bản dịch


@dataclass(frozen=True, slots=True)
class TermBrief:
    pinyin: str | None
    meaning_vi: str | None  # nghĩa thô của từ điển, chưa rút gọn


class ChapterSource(Protocol):
    """Các trang của chương mà người gọi đọc được (M03). Không đọc được → NotFoundError (404)."""

    async def pages_of(self, identity: Identity, chapter_id: int) -> list[ChapterPage]: ...


class TermHints(Protocol):
    """Tra cứu từ điển M06 theo lô."""

    async def hsk_levels(self, terms: Sequence[str]) -> dict[str, int | None]: ...

    async def briefs(self, terms: Sequence[str]) -> dict[str, TermBrief]: ...

    async def known_terms(self, terms: Sequence[str]) -> set[str]:
        """Tập con của `terms` có mục trong từ điển (dùng để gộp dạng lặp về từ gốc)."""
        ...


class SeriesCandidateSource(Protocol):
    """Truyện công khai ứng viên từ M03 qua giao diện công khai của M03 (F10.04)."""

    async def candidates(self, identity: Identity, hsk_min: int, hsk_max: int) -> list[SeriesCandidate]: ...


class LearnerLevelSource(Protocol):
    async def hsk_level_of(self, user_id: int) -> int | None:
        """Trình độ HSK đã khai báo (M02); chưa khai báo thì None."""
        ...


class WordSaver(Protocol):
    """Lưu từ vào sổ tay: `SaveWordUseCase` của M07 (F07.01, F07.02)."""

    async def execute(self, identity: Identity, command: SaveWordCommand) -> SaveWordResult: ...


class SavedTermSource(Protocol):
    async def saved_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        """Tập con của `terms` đã có trong sổ tay (mọi trạng thái)."""
        ...


class LookupCounter(Protocol):
    async def count_by_term(self, user_id: int, terms: Sequence[str]) -> dict[str, int]: ...


class DismissedRepository(Protocol):
    async def terms(self, user_id: int) -> set[str]: ...

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[DismissedTerm], int]:
        """Bỏ qua gần nhất trước."""
        ...

    async def add(self, user_id: int, term: str, now: datetime) -> None:
        """Idempotent: đã có thì giữ nguyên."""
        ...

    async def remove(self, user_id: int, term: str) -> None:
        """Không có thì bỏ qua, không lỗi."""
        ...


class SuggestionUnitOfWork(Protocol):
    @property
    def dismissed(self) -> DismissedRepository: ...

    @property
    def bubbles(self) -> BubbleRepository: ...

    @property
    def saved(self) -> SavedTermSource: ...

    @property
    def lookups(self) -> LookupCounter: ...

    async def __aenter__(self) -> SuggestionUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
