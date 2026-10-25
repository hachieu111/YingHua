"""Lỗi nghiệp vụ của M01 (thông điệp theo docs/modules-functions.md §4.1)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, PermissionDeniedError, UnauthenticatedError


class EmailAlreadyUsedError(ConflictError):
    code = "EMAIL_ALREADY_USED"
    default_message = "Email đã được sử dụng"


class WeakPasswordError(InvalidInputError):
    code = "WEAK_PASSWORD"
    default_message = "Mật khẩu tối thiểu 8 ký tự"


class DisplayNameRequiredError(InvalidInputError):
    code = "DISPLAY_NAME_REQUIRED"
    default_message = "Tên hiển thị là trường bắt buộc"


class InvalidCredentialsError(UnauthenticatedError):
    code = "INVALID_CREDENTIALS"
    default_message = "Email hoặc mật khẩu không đúng"


class AccountLockedError(PermissionDeniedError):
    code = "ACCOUNT_LOCKED"
    default_message = "Tài khoản đã bị khóa, vui lòng liên hệ quản trị viên"


class SessionExpiredError(UnauthenticatedError):
    code = "SESSION_EXPIRED"
    default_message = "Phiên đã hết hạn"


class WrongCurrentPasswordError(InvalidInputError):
    code = "WRONG_CURRENT_PASSWORD"
    default_message = "Mật khẩu hiện tại không đúng"


class SamePasswordError(InvalidInputError):
    code = "SAME_PASSWORD"
    default_message = "Mật khẩu mới phải khác mật khẩu cũ"


class ResetLinkInvalidError(InvalidInputError):
    code = "RESET_LINK_INVALID"
    default_message = "Liên kết đặt lại mật khẩu không còn hiệu lực"
