"""Lỗi nghiệp vụ của M05 (thông điệp theo docs/modules-functions.md §5)."""

from __future__ import annotations

from app.core.errors import InvalidInputError, NotFoundError, PayloadTooLargeError, RateLimitedError


class BubbleNotFoundError(NotFoundError):
    code = "BUBBLE_NOT_FOUND"
    default_message = "Không tìm thấy vùng chữ"


class EmptyTranslationError(InvalidInputError):
    code = "EMPTY_TRANSLATION"
    default_message = "Bản dịch không được để trống"


class EditTooLongError(InvalidInputError):
    code = "EDIT_TOO_LONG"
    default_message = "Bản dịch quá dài"


class WordNotInBubbleError(InvalidInputError):
    code = "WORD_NOT_IN_BUBBLE"
    default_message = "Từ cần tra không nằm trong vùng chữ này"


class GuestLookupLimitReachedError(RateLimitedError):
    code = "GUEST_LOOKUP_LIMIT_REACHED"
    default_message = "Bạn đã dùng hết lượt tra thử. Vui lòng đăng ký hoặc đăng nhập để tra không giới hạn"


class InvalidAnnotationError(InvalidInputError):
    code = "INVALID_ANNOTATION"
    default_message = "Ghi chú trên trang không hợp lệ"


class AnnotationTooLargeError(PayloadTooLargeError):
    code = "ANNOTATION_TOO_LARGE"
    default_message = "Ghi chú trên trang quá lớn"
