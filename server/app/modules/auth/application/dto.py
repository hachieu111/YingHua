from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.modules.auth.domain.entities import Role, User


@dataclass(frozen=True, slots=True)
class AuthConfig:
    refresh_ttl: timedelta
    short_refresh_ttl: timedelta  # hạn mã làm mới khi không ghi nhớ đăng nhập (F01.11)
    reset_ttl: timedelta
    access_expires_in: int  # giây
    frontend_url: str
    login_max_attempts_per_email: int
    login_max_attempts_per_ip: int


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    remember_me: bool = True  # giao diện lưu bền (true) hay chỉ sessionStorage (false)


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    tokens: TokenPair


@dataclass(frozen=True, slots=True)
class Identity:
    """Danh tính người gọi sau khi xác thực (F01.09)."""

    user_id: int
    role: Role
    session_id: str

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN
