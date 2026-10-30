from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.modules.imaging.domain.entities import NewBubble, QueueStats, Translation, TranslationStatus


@dataclass(frozen=True, slots=True)
class TranslationSummary:
    id: int
    status: TranslationStatus
    inpainted_file_id: int | None = None
    rendered_file_id: int | None = None
    error_step: str | None = None
    error_message: str | None = None
    # Chữ đã đọc xong (giai đoạn 1): bản dịch `done` hoặc đã có bong bóng dù đang `running`/`failed`.
    text_ready: bool = False


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Tham số hàng đợi lấy từ Settings (JOB_MAX_ATTEMPTS, JOB_STALE_MINUTES)."""

    max_attempts: int = 2
    stale_after: timedelta = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    """Việc worker vừa nhận. Đọc ảnh gốc bằng `FileStorage.read(source_storage_key)`."""

    translation_id: int
    source_file_id: int
    source_storage_key: str
    source_mime_type: str
    sha256: str
    attempts: int  # đã tính cả lần này (lần đầu = 1)
    queued_at: datetime


@dataclass(frozen=True, slots=True)
class JobResult:
    """Kết quả pipeline cho `complete_job`. Ảnh dẫn xuất đã lưu trước bằng `store_result_image`.

    Nếu bản dịch đã có bong bóng (do `save_text_result` ở giai đoạn 1) thì `complete_job` chỉ cập nhật
    `style` theo `idx`, giữ nguyên id bong bóng; chưa có thì chèn `bubbles` như trước.
    """

    bubbles: Sequence[NewBubble]
    inpainted_file_id: int | None = None
    rendered_file_id: int | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    processing_ms: int = 0
    phash: int | None = None


@dataclass(frozen=True, slots=True)
class PageStatus:
    page_id: int
    translation_id: int | None
    status: TranslationStatus | None
    attempts: int
    error_step: str | None
    error_message: str | None
    can_retranslate: bool
    text_ready: bool = False


@dataclass(frozen=True, slots=True)
class RequeueResult:
    page_id: int | None
    translation_id: int
    status: TranslationStatus


@dataclass(frozen=True, slots=True)
class DownloadedImage:
    data: bytes
    mime_type: str
    filename: str


@dataclass(frozen=True, slots=True)
class TranslationList:
    items: list[Translation]
    total: int
    stats: QueueStats
