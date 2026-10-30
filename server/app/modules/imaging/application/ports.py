"""Giao diện (port) mà tầng hạ tầng của M04 phải hiện thực."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from app.core.stored_files import StoredFileRepository
from app.modules.imaging.application.dto import TranslationSummary
from app.modules.imaging.domain.entities import (
    Bubble,
    NewBubble,
    QueueStats,
    Translation,
    TranslationStatus,
)


class TranslationRepository(Protocol):
    """Phần mà M03 dùng: xếp hàng, dùng lại bản dịch, tóm tắt trạng thái, dọn khi xóa trang."""

    async def enqueue(self, source_file_id: int, sha256: str, now: datetime) -> int:
        """Tạo bản dịch `queued` cho một ảnh; trả id (F04.01)."""
        ...

    async def find_done_by_sha256(self, sha256: str) -> int | None:
        """Bản dịch `done` của ảnh cùng nội dung, để dùng lại (F04.14)."""
        ...

    async def get_summaries(self, translation_ids: Sequence[int]) -> dict[int, TranslationSummary]: ...

    async def translation_ids_of_file(self, file_id: int) -> list[int]:
        """Các bản dịch dùng `file_id` làm ảnh đã xóa chữ hoặc ảnh đã dịch."""
        ...

    async def delete_many(self, translation_ids: Sequence[int]) -> list[int]:
        """Xóa bản dịch (kéo theo bong bóng); trả id các tệp dẫn xuất cần xóa."""
        ...


class TranslationQueue(Protocol):
    """Hàng đợi công việc dựa trên bảng `translations` (F04.03, F04.05–F04.07, F04.13)."""

    async def get(self, translation_id: int) -> Translation | None: ...

    async def get_for_update(self, translation_id: int) -> Translation | None:
        """Khóa dòng để hai yêu cầu đồng thời không cùng đổi trạng thái."""
        ...

    async def requeue_failed(self, translation_id: int, now: datetime) -> bool:
        """Nguyên tử: `failed` → `queued`, xóa số lần thử và lý do lỗi. False nếu không còn ở `failed`."""
        ...

    async def claim_next(self, worker_id: str, now: datetime, stale_before: datetime) -> Translation | None:
        """`SELECT ... FOR UPDATE SKIP LOCKED` việc `queued` cũ nhất (hoặc `running` bị bỏ quên từ trước
        `stale_before`), đặt `running`, `started_at`, `attempts + 1`, `worker_id`."""
        ...

    async def fail_exhausted_stale(self, stale_before: datetime, now: datetime, max_attempts: int) -> int:
        """Việc `running` bị bỏ quên đã hết lượt thử → `failed`. Trả số việc đã đóng."""
        ...

    async def save_partial_stats(self, translation_id: int, stats: dict[str, Any]) -> None:
        """Ghi thống kê giai đoạn 1 khi việc vẫn `running`."""
        ...

    async def mark_done(
        self,
        translation_id: int,
        inpainted_file_id: int | None,
        rendered_file_id: int | None,
        stats: dict[str, Any],
        processing_ms: int,
        phash: int | None,
        now: datetime,
    ) -> None: ...

    async def mark_failed(
        self, translation_id: int, step: str, message: str, requeue: bool, now: datetime
    ) -> TranslationStatus:
        """Ghi lỗi; `requeue` đặt lại `queued` (còn lượt thử), ngược lại `failed`. Trả trạng thái mới."""
        ...

    async def list_page(
        self, status: TranslationStatus | None, offset: int, limit: int
    ) -> tuple[list[Translation], int]: ...

    async def stats(self) -> QueueStats: ...

    async def orphan_result_file_ids(self, created_before: datetime, limit: int) -> list[int]:
        """Tệp `inpainted`/`rendered` không bản dịch nào tham chiếu, đã lưu từ trước `created_before`."""
        ...


class BubbleRepository(Protocol):
    async def list_by_translation(self, translation_id: int) -> list[Bubble]: ...

    async def get(self, bubble_id: int) -> Bubble | None: ...

    async def get_many(self, bubble_ids: Sequence[int]) -> dict[int, Bubble]: ...

    async def delete_by_translation(self, translation_id: int) -> int: ...

    async def count_by_translation(self, translation_id: int) -> int: ...

    async def update_styles(self, translation_id: int, styles: dict[int, Any]) -> None:
        """Cập nhật `style` theo `idx`; id và nội dung chữ của bong bóng giữ nguyên."""
        ...

    async def add_many(self, translation_id: int, bubbles: Sequence[NewBubble]) -> None: ...


class AuditLog(Protocol):
    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None: ...


class ImagingUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def translations(self) -> TranslationQueue: ...

    @property
    def bubbles(self) -> BubbleRepository: ...

    @property
    def files(self) -> StoredFileRepository: ...

    @property
    def audit(self) -> AuditLog: ...

    async def __aenter__(self) -> ImagingUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
