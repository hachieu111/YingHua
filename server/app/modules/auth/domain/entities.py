"""Thực thể của M01 — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"


@dataclass(slots=True)
class User:
    id: int
    email: str
    password_hash: str
    display_name: str
    role: Role
    status: UserStatus
    created_at: datetime
    chinese_name: str | None = None
    avatar_file_id: int | None = None
    avatar_preset: str | None = None  # mã ảnh có sẵn (F01.10); loại trừ với avatar_file_id
    show_email: bool = True
    show_join_date: bool = True
    locked_reason: str | None = None
    locked_at: datetime | None = None
    password_changed_at: datetime | None = None
    last_login_at: datetime | None = None

    @property
    def is_locked(self) -> bool:
        return self.status is UserStatus.LOCKED


@dataclass(frozen=True, slots=True)
class NewUser:
    email: str
    password_hash: str
    display_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshSession:
    """Một mã làm mới. Các mã cùng `family_id` thuộc cùng một phiên đăng nhập trên một thiết bị."""

    id: int
    user_id: int
    family_id: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NewRefreshSession:
    user_id: int
    family_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime
    user_agent: str | None = None
    ip: str | None = None


@dataclass(frozen=True, slots=True)
class PasswordResetToken:
    id: int
    user_id: int
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
