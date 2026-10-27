"""Quy tắc nghiệp vụ thuần của tài khoản."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.auth.domain.errors import DisplayNameRequiredError, WeakPasswordError

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # chặn mật khẩu quá dài làm chậm bước băm
DISPLAY_NAME_MAX_LENGTH = 100

# Ảnh đại diện có sẵn (F01.10 mở rộng, US-NH-65 TC6): mã -> tên hiển thị.
# Ảnh tĩnh nằm ở frontend, khớp theo mã.
AVATAR_PRESETS: dict[str, str] = {
    "original": "Lam Hiên Vũ",
    "sakura_flower": "Hoa Anh Đào Yinghua",
    "bach_thien": "Bạch Thiển (Quán quân)",
    "tieu_vu_tru": "Tiểu Vũ Trụ",
    "mac_van": "Mạc Vấn",
    "lac_ly": "Lạc Ly",
}


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


def is_remembered_session(created_at: datetime, expires_at: datetime, short_ttl: timedelta) -> bool:
    """Phiên "ghi nhớ đăng nhập" (F01.11) nếu hạn dài hơn hạn phiên ngắn; không cần thêm cột lưu cờ."""
    return expires_at - created_at > short_ttl
