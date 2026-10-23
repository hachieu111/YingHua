"""Lỗi nghiệp vụ dùng chung. Tầng api ánh xạ `kind` sang mã HTTP (exception_handlers.py)."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar


class ErrorKind(str, Enum):
    INVALID_INPUT = "invalid_input"
    UNAUTHENTICATED = "unauthenticated"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    RATE_LIMITED = "rate_limited"
    EXTERNAL_SERVICE = "external_service"


class DomainError(Exception):
    """Gốc của mọi lỗi nghiệp vụ. Lớp con đặt `kind`, `code` và thông điệp mặc định tiếng Việt."""

    kind: ClassVar[ErrorKind] = ErrorKind.INVALID_INPUT
    code: ClassVar[str] = "INVALID_INPUT"
    default_message: ClassVar[str] = "Dữ liệu không hợp lệ"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class InvalidInputError(DomainError):
    pass


class UnauthenticatedError(DomainError):
    kind = ErrorKind.UNAUTHENTICATED
    code = "UNAUTHENTICATED"
    default_message = "Bạn cần đăng nhập"


class PermissionDeniedError(DomainError):
    kind = ErrorKind.PERMISSION_DENIED
    code = "PERMISSION_DENIED"
    default_message = "Bạn không có quyền thực hiện thao tác này"


class NotFoundError(DomainError):
    kind = ErrorKind.NOT_FOUND
    code = "NOT_FOUND"
    default_message = "Không tìm thấy dữ liệu"


class ConflictError(DomainError):
    kind = ErrorKind.CONFLICT
    code = "CONFLICT"
    default_message = "Dữ liệu bị trùng hoặc xung đột"


class PayloadTooLargeError(DomainError):
    kind = ErrorKind.PAYLOAD_TOO_LARGE
    code = "PAYLOAD_TOO_LARGE"
    default_message = "Tệp quá lớn"


class RateLimitedError(DomainError):
    kind = ErrorKind.RATE_LIMITED
    code = "RATE_LIMITED"
    default_message = "Bạn thao tác quá nhanh, vui lòng thử lại sau"


class ExternalServiceError(DomainError):
    kind = ErrorKind.EXTERNAL_SERVICE
    code = "EXTERNAL_SERVICE_UNAVAILABLE"
    default_message = "Dịch vụ bên ngoài tạm thời không khả dụng"
