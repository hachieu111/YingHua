from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.modules.admin.application.dto import (
    AuditLogFilter,
    AuditLogItem,
    ModerationTarget,
    RemovalItem,
    SamplePageCandidate,
    UploadItem,
    UserActivity,
)
from app.modules.auth.application.public import Identity, SessionRepository, UserRepository


class ContentOwnerNotifier(Protocol):
    """Báo cho người tải ảnh biết ảnh/trang của họ bị gỡ (F13.04, F14.05); M14 hiện thực qua adapter."""

    async def content_removed(self, owner_id: int, page_id: int | None, reason: str) -> None: ...


class AuditLogRepository(Protocol):
    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None:
        """Bản ghi chỉ thêm (F13.06): không có thao tác sửa hay xóa."""
        ...


class AuditLogReader(Protocol):
    async def search(
        self, filters: AuditLogFilter, offset: int, limit: int
    ) -> tuple[list[AuditLogItem], int]:
        """Mới nhất trước; trả (trang, tổng số khớp)."""
        ...


class SystemSettingsRepository(Protocol):
    async def load_all(self) -> dict[str, Any]:
        """Giá trị thô của các khóa đã được đặt trong CSDL."""
        ...

    async def upsert_many(self, values: dict[str, Any], admin_id: int, at: datetime) -> None: ...

    async def delete_many(self, keys: list[str]) -> None:
        """Xóa khóa đã đặt để quay về mặc định."""
        ...

    async def is_valid_sample_page(self, page_id: int) -> bool:
        """Trang tồn tại, thuộc truyện công khai, bản dịch `done` và ảnh chưa bị gỡ (F04.16)."""
        ...

    async def list_sample_page_candidates(self, limit: int) -> list[SamplePageCandidate]:
        """Các trang thỏa `is_valid_sample_page`, mới nhất trước, tối đa `limit` trang."""
        ...


class ModerationRepository(Protocol):
    """Kiểm duyệt ảnh (F13.04): hàng chờ, gỡ và nhật ký gỡ."""

    async def list_uploads(
        self, auto_flags: bool, flagged_only: bool, offset: int, limit: int
    ) -> tuple[list[UploadItem], int]:
        """Ảnh gốc chưa bị gỡ, mới nhất trước. `auto_flags` tắt thì không tính cờ nghi vấn."""
        ...

    async def resolve_target(self, page_id: int | None, file_id: int | None) -> ModerationTarget | None: ...

    async def mark_removed(self, file_ids: list[int], at: datetime) -> list[int]:
        """Đặt `removed_at` cho tệp chưa bị gỡ; trả mã các tệp vừa được gỡ."""
        ...

    async def add_removal(
        self, file_id: int | None, page_id: int | None, reason: str, removed_by: int, at: datetime
    ) -> int: ...

    async def get_removal(self, removal_id: int) -> RemovalItem: ...

    async def list_removals(self, offset: int, limit: int) -> tuple[list[RemovalItem], int]: ...


class UserActivitySource(Protocol):
    """Gom số liệu của một người dùng từ các module sở hữu dữ liệu (M03, M07, M08)."""

    async def collect(self, actor: Identity, user_id: int) -> UserActivity: ...


class AdminUnitOfWork(Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    @property
    def audit_logs(self) -> AuditLogReader: ...

    @property
    def system_settings(self) -> SystemSettingsRepository: ...

    @property
    def moderation(self) -> ModerationRepository: ...

    async def __aenter__(self) -> AdminUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
