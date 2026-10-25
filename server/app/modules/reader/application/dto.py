from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.dictionary.application.public import LookupResult
from app.modules.imaging.application.public import Bubble, TranslationSummary
from app.modules.library.application.public import PageAccess
from app.modules.reader.domain.entities import Annotation, GuestQuota


@dataclass(frozen=True, slots=True)
class ReadingBubble:
    bubble: Bubble
    edited_text: str | None  # bản sửa dịch riêng của người gọi

    @property
    def text_vi_effective(self) -> str | None:
        return self.edited_text if self.edited_text is not None else self.bubble.text_vi


@dataclass(frozen=True, slots=True)
class ReadingView:
    access: PageAccess
    translation: TranslationSummary | None
    bubbles: list[ReadingBubble]
    annotation: Annotation | None  # None với Khách


@dataclass(frozen=True, slots=True)
class BubbleLookup:
    bubble_id: int
    word: str
    result: LookupResult
    guest: GuestQuota | None


@dataclass(frozen=True, slots=True)
class EditedBubble:
    bubble: Bubble
    edited_text: str | None

    @property
    def text_vi_effective(self) -> str | None:
        return self.edited_text if self.edited_text is not None else self.bubble.text_vi


@dataclass(frozen=True, slots=True)
class BookmarkItem:
    access: PageAccess
    bookmarked_at: datetime


@dataclass(frozen=True, slots=True)
class BookmarkPage:
    items: list[BookmarkItem]
    total: int
