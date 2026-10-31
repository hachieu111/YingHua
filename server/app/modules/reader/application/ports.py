"""Giao diện (port) mà tầng hạ tầng của M05 phải hiện thực."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.modules.admin.application.public import AuditLogRepository
from app.modules.auth.application.public import Identity
from app.modules.dictionary.application.public import LookupResult
from app.modules.imaging.application.public import BubbleRepository, TranslationRepository
from app.modules.reader.domain.entities import (
    Annotation,
    AnnotationInput,
    BookmarkRef,
    ConsumeOutcome,
)
from app.modules.reader.domain.grammar import GrammarAnalysis, GrammarContent


class BubbleEditRepository(Protocol):
    async def get_many(self, user_id: int, bubble_ids: Sequence[int]) -> dict[int, str]:
        """Bản sửa dịch của riêng người dùng, theo mã bong bóng."""
        ...

    async def upsert(self, user_id: int, bubble_id: int, text_vi: str, now: datetime) -> None: ...

    async def delete(self, user_id: int, bubble_id: int) -> bool:
        """True nếu có bản sửa bị xóa."""
        ...


class AnnotationRepository(Protocol):
    async def get(self, user_id: int, page_id: int) -> Annotation | None: ...

    async def set_bookmark(self, user_id: int, page_id: int, value: bool, now: datetime) -> Annotation:
        """Tạo dòng nếu chưa có; giữ nguyên ghi chú đã có."""
        ...

    async def save(self, user_id: int, page_id: int, data: AnnotationInput, now: datetime) -> Annotation:
        """Thay toàn bộ tô màu và nét vẽ; giữ nguyên dấu trang."""
        ...

    async def clear(self, user_id: int, page_id: int, now: datetime) -> None:
        """Xóa tô màu và nét vẽ, giữ dấu trang; dòng không còn gì thì bị xóa hẳn."""
        ...

    async def list_bookmarked(
        self, user_id: int, offset: int, limit: int
    ) -> tuple[list[BookmarkRef], int]: ...


class GuestSessionRepository(Protocol):
    async def consume(self, session_id: uuid.UUID, limit: int, now: datetime) -> tuple[ConsumeOutcome, int]:
        """Nguyên tử: tăng bộ đếm nếu phiên còn hạn và chưa chạm `limit`. Trả (kết quả, số lượt đã dùng)."""
        ...

    async def create(self, now: datetime, expires_at: datetime, used: int) -> uuid.UUID: ...

    async def delete_expired(self, now: datetime) -> int: ...


class DictionaryLookup(Protocol):
    """Tra từ qua M06 (kèm cài đặt hiển thị của người dùng)."""

    async def lookup(
        self, term: str, identity: Identity | None, bubble_id: int | None = None
    ) -> LookupResult: ...


@dataclass(frozen=True, slots=True)
class GrammarRequest:
    """Dữ liệu gửi LLM để phân tích một câu: chỉ câu chữ Hán và bản dịch tự động dùng chung (nếu có).

    Không có bản sửa dịch cá nhân, ghi chú, trình độ hay mã người dùng (security.md; kết quả dùng chung).
    """

    sentence: str
    translation_vi: str | None = None


class GrammarAnalyzer(Protocol):
    """Dịch vụ phân tích ngữ pháp (LLM, F05.09). Hiện thực chuyển mọi lỗi hạ tầng thành
    `GrammarAnalyzerUnavailableError`. Trả JSON đã phân tích (hoặc `None` nếu không đọc được); việc kiểm
    lược đồ thuộc `domain.grammar`, nên kết quả sai không bao giờ vào CSDL."""

    async def analyze(self, request: GrammarRequest) -> object: ...


class SentenceLevelChecker(Protocol):
    """Độ khó câu: cấp HSK cao nhất của các từ trong câu (jieba + bảng HSK của M06)."""

    async def difficulties(self, sentences: Sequence[str]) -> list[int | None]: ...


class LearnerTimezoneSource(Protocol):
    async def timezone_of(self, user_id: int) -> str | None:
        """Múi giờ đã khai báo (M02); dùng để tính "một ngày" của hạn mức."""
        ...


class GrammarRepository(Protocol):
    async def get_by_hash(self, sentence_hash: str) -> GrammarAnalysis | None: ...

    async def add(
        self, sentence_hash: str, sentence: str, content: GrammarContent, model: str | None
    ) -> GrammarAnalysis:
        """Lưu kết quả đã kiểm; câu đã có (hai người cùng lúc) thì trả bản có sẵn."""
        ...

    async def add_request(self, user_id: int, analysis_id: int | None, requested_at: datetime) -> None:
        """Ghi một lượt đã phải gọi LLM (để tính hạn mức); `analysis_id` None khi lỗi hoặc kết quả bị loại."""
        ...

    async def count_requests_between(self, user_id: int, start: datetime, end: datetime) -> int: ...


class ReaderUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def grammar(self) -> GrammarRepository: ...

    @property
    def edits(self) -> BubbleEditRepository: ...

    @property
    def annotations(self) -> AnnotationRepository: ...

    @property
    def guests(self) -> GuestSessionRepository: ...

    @property
    def bubbles(self) -> BubbleRepository: ...

    @property
    def translations(self) -> TranslationRepository: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    async def __aenter__(self) -> ReaderUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
