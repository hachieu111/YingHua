"""Lỗi nghiệp vụ của M14 (thông điệp theo docs/modules-functions.md §4.14)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class ReportContentRequiredError(InvalidInputError):
    code = "REPORT_CONTENT_REQUIRED"
    default_message = "Hãy chọn loại lỗi hoặc mô tả vấn đề"


class InvalidReportTypeError(InvalidInputError):
    code = "INVALID_REPORT_TYPE"
    default_message = "Loại lỗi không hợp lệ (ocr, translation hoặc other)"


class InvalidReportStatusError(InvalidInputError):
    code = "INVALID_REPORT_STATUS"
    default_message = 'Chỉ có thể chuyển báo lỗi sang "resolved" (Đã xử lý) hoặc "rejected" (Từ chối)'


class ReportTextTooLongError(InvalidInputError):
    code = "REPORT_TEXT_TOO_LONG"
    default_message = "Nội dung quá dài"


class DuplicateReportError(ConflictError):
    code = "REPORT_ALREADY_EXISTS"
    default_message = "Bạn đã báo lỗi này và báo lỗi cũ vẫn đang chờ xử lý"


class ReportNotFoundError(NotFoundError):
    code = "REPORT_NOT_FOUND"
    default_message = "Không tìm thấy báo lỗi"


class ReportAlreadyHandledError(ConflictError):
    code = "REPORT_ALREADY_HANDLED"
    default_message = "Báo lỗi này đã được xử lý"


class ReportBubbleNotFoundError(NotFoundError):
    code = "BUBBLE_NOT_FOUND"
    default_message = "Không tìm thấy bong bóng trên trang này"


class NotificationNotFoundError(NotFoundError):
    code = "NOTIFICATION_NOT_FOUND"
    default_message = "Không tìm thấy thông báo"


class EmailDeliveryError(Exception):
    """Gửi email thất bại (hạ tầng). Không lộ ra API: thông báo trong ứng dụng vẫn được giữ (F14.05)."""
