"""Quy tắc nghiệp vụ thuần của tài khoản."""

from __future__ import annotations

from app.modules.auth.domain.errors import DisplayNameRequiredError, WeakPasswordError

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # chặn mật khẩu quá dài làm chậm bước băm
DISPLAY_NAME_MAX_LENGTH = 100


def normalize_email(email: str) -> str:
    """Email so khớp không phân biệt hoa thường (F01.01 bước 3)."""
    return email.strip().lower()


def validate_password(plain: str) -> None:
    if len(plain) < PASSWORD_MIN_LENGTH or len(plain) > PASSWORD_MAX_LENGTH:
        raise WeakPasswordError()


def clean_display_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise DisplayNameRequiredError()
    return cleaned[:DISPLAY_NAME_MAX_LENGTH]


def default_display_name(email: str) -> str:
    """Tên hiển thị ban đầu: phần trước dấu @ của email (F01.01 bước 5)."""
    return clean_display_name(email.split("@", 1)[0] or "Người học")
