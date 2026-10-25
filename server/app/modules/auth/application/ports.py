"""Giao diện (port) mà tầng hạ tầng của M01 phải hiện thực."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.core.stored_files import StoredFileRepository
from app.modules.auth.domain.entities import (
    NewRefreshSession,
    NewUser,
    PasswordResetToken,
    RefreshSession,
    User,
)


class UserRepository(Protocol):
    async def get(self, user_id: int) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None:
        """`email` đã chuẩn hóa chữ thường."""
        ...

    async def add(self, new_user: NewUser) -> User:
        """Raise EmailAlreadyUsedError nếu email đã tồn tại."""
        ...

    async def update(self, user: User) -> None: ...

    async def search(self, query: str | None, offset: int, limit: int) -> tuple[list[User], int]:
        """Tìm theo email chứa `query`; trả (danh sách trang, tổng số khớp)."""
        ...


class SessionRepository(Protocol):
    async def add(self, new_session: NewRefreshSession) -> RefreshSession: ...

    async def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        """Khóa dòng để hai yêu cầu làm mới đồng thời không cùng xoay vòng một mã."""
        ...

    async def mark_replaced(self, session_id: int, replaced_by_id: int) -> None: ...

    async def is_family_active(self, family_id: str, now: datetime) -> bool: ...

    async def revoke_family(self, family_id: str, at: datetime) -> None: ...

    async def revoke_user_sessions(self, user_id: int, at: datetime, except_family: str | None = None) -> int:
        """Thu hồi mọi phiên còn hiệu lực của người dùng; trả số phiên (thiết bị) đã thu hồi."""
        ...

    async def delete_expired(self, now: datetime, revoked_before: datetime) -> int:
        """Xóa mã làm mới hết hạn hoặc đã thu hồi từ trước `revoked_before`; trả số dòng xóa (F15.02)."""
        ...


class PasswordResetRepository(Protocol):
    async def add(
        self, user_id: int, token_hash: str, expires_at: datetime, created_at: datetime
    ) -> None: ...

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None: ...

    async def mark_used(self, token_id: int, at: datetime) -> None: ...

    async def delete_expired(self, now: datetime) -> int:
        """Xóa liên kết đặt lại mật khẩu đã hết hạn; trả số dòng đã xóa (F15.02)."""
        ...


class EmailSender(Protocol):
    async def send_password_reset(self, to_email: str, reset_link: str) -> None: ...


class AuthUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def users(self) -> UserRepository: ...

    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def resets(self) -> PasswordResetRepository: ...

    @property
    def files(self) -> StoredFileRepository: ...

    async def __aenter__(self) -> AuthUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
