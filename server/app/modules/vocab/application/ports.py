"""Giao diện (port) mà tầng hạ tầng của M07 phải hiện thực."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.core.image_validation import ImageUpload
from app.core.learning_events import LearningEventPort
from app.core.stored_files import StoredFileRepository
from app.modules.admin.application.public import AuditLogRepository
from app.modules.imaging.application.public import BubbleRepository
from app.modules.reader.application.public import BubbleEditRepository
from app.modules.review.application.public import CardRepository
from app.modules.stats.application.public import ActivityRecorder
from app.modules.vocab.domain.entities import (
    ContextSummary,
    CropBox,
    NewSavedSentence,
    NewVocabContext,
    NewVocabEntry,
    SavedSentence,
    VocabContext,
    VocabEntry,
    VocabFilter,
)


@dataclass(frozen=True, slots=True)
class TermInfo:
    """Thông tin từ điển của một từ để điền sổ tay (F06.08, F07.01)."""

    entry_id: int | None
    pinyin: str | None
    meaning_vi: str | None
    hsk_level: int | None
    hsk_source: str  # list | derived | none


class TermDictionary(Protocol):
    """Tra từ điển M06 theo nhu cầu của sổ tay."""

    async def describe(self, term: str) -> TermInfo: ...

    async def sino_vietnamese(self, terms: Sequence[str]) -> dict[str, str]:
        """Âm Hán Việt theo từ, ghép từ âm từng chữ; từ thiếu dữ liệu thì vắng mặt."""
        ...


class SnippetCropper(Protocol):
    async def crop(self, image: bytes, box: CropBox) -> ImageUpload:
        """Cắt `box` khỏi ảnh gốc, thu nhỏ nếu quá lớn. Raise DomainError nếu ảnh hỏng."""
        ...


class VocabRepository(Protocol):
    """Mọi truy vấn lọc theo `user_id` của người đang đăng nhập."""

    async def get(self, user_id: int, entry_id: int) -> VocabEntry | None: ...

    async def get_many(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, VocabEntry]: ...

    async def get_by_term(self, user_id: int, term: str) -> VocabEntry | None: ...

    async def add_if_absent(self, new_entry: NewVocabEntry) -> VocabEntry | None:
        """`INSERT ... ON CONFLICT (user_id, term) DO NOTHING`: None nếu từ đã có (kể cả đồng thời)."""
        ...

    async def update(self, entry: VocabEntry) -> None: ...

    async def delete(self, user_id: int, entry_id: int) -> None:
        """Kéo theo ngữ cảnh, thẻ và lượt ôn nhờ khóa ngoại `ON DELETE CASCADE`."""
        ...

    async def search(self, flt: VocabFilter, offset: int, limit: int) -> tuple[list[VocabEntry], int]: ...

    async def starred_ids(self, user_id: int) -> list[int]: ...

    async def terms_with_context_on_page(self, user_id: int, page_id: int, terms: Sequence[str]) -> set[str]:
        """Trong `terms`, những từ đã có ngữ cảnh lấy từ trang `page_id`."""
        ...

    async def existing_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        """Tập con của `terms` đã có trong sổ tay, mọi trạng thái."""
        ...


class VocabContextRepository(Protocol):
    async def add_if_absent(self, new_context: NewVocabContext) -> VocabContext | None:
        """`ON CONFLICT (vocab_entry_id, bubble_id) DO NOTHING`: None nếu bong bóng này đã có ngữ cảnh."""
        ...

    async def has_bubble(self, vocab_entry_id: int, bubble_id: int) -> bool: ...

    async def list_for_entry(self, vocab_entry_id: int) -> list[VocabContext]:
        """Mới nhất trước."""
        ...

    async def get(self, vocab_entry_id: int, context_id: int) -> VocabContext | None: ...

    async def delete(self, context_id: int) -> None: ...

    async def summaries(self, entry_ids: Sequence[int]) -> dict[int, ContextSummary]: ...

    async def snippet_file_ids(self, vocab_entry_id: int) -> list[int]: ...

    async def page_links(self, user_id: int) -> list[tuple[int, int]]:
        """Cặp (mã mục từ, mã trang) của mọi ngữ cảnh còn gắn với một trang."""
        ...

    async def entry_ids_for_pages(self, user_id: int, page_ids: Sequence[int]) -> list[int]: ...


class SavedSentenceRepository(Protocol):
    """Câu thoại đã lưu (F07.11); mọi truy vấn lọc theo `user_id`."""

    async def add_if_absent(self, new: NewSavedSentence) -> SavedSentence | None:
        """`ON CONFLICT (user_id, bubble_id) DO NOTHING`: None nếu bong bóng này đã được lưu."""
        ...

    async def get(self, user_id: int, sentence_id: int) -> SavedSentence | None: ...

    async def get_by_bubble(self, user_id: int, bubble_id: int) -> SavedSentence | None: ...

    async def saved_bubble_ids(self, user_id: int, bubble_ids: Sequence[int]) -> set[int]:
        """Trong `bubble_ids`, những bong bóng người dùng đã lưu câu thoại."""
        ...

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[SavedSentence], int]:
        """Mới nhất trước."""
        ...

    async def update_note(self, user_id: int, sentence_id: int, note: str | None, now: datetime) -> None: ...

    async def delete(self, user_id: int, sentence_id: int) -> None: ...


class VocabUnitOfWork(Protocol):
    """Một giao dịch dùng chung với M08 (thẻ) và các kho dùng chung. Không commit thì mọi thay đổi bị hủy."""

    @property
    def entries(self) -> VocabRepository: ...

    @property
    def contexts(self) -> VocabContextRepository: ...

    @property
    def cards(self) -> CardRepository: ...

    @property
    def files(self) -> StoredFileRepository: ...

    @property
    def bubbles(self) -> BubbleRepository: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    @property
    def sentences(self) -> SavedSentenceRepository: ...

    @property
    def edits(self) -> BubbleEditRepository: ...

    @property
    def activity(self) -> ActivityRecorder: ...

    @property
    def learning(self) -> LearningEventPort: ...

    async def __aenter__(self) -> VocabUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
