"""Lỗi nghiệp vụ của M04 (thông điệp theo docs/modules-functions.md §4)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class TranslationNotFoundError(NotFoundError):
    code = "TRANSLATION_NOT_FOUND"
    default_message = "Không tìm thấy bản dịch"


class TranslationInProgressError(ConflictError):
    code = "TRANSLATION_IN_PROGRESS"
    default_message = "Trang đang được xử lý, vui lòng chờ"


class TranslationNotFailedError(ConflictError):
    code = "TRANSLATION_NOT_FAILED"
    default_message = "Trang không ở trạng thái lỗi nên không cần xử lý lại"


class PageNotProcessedError(ConflictError):
    code = "PAGE_NOT_PROCESSED"
    default_message = "Trang chưa được xử lý xong"


class ImageNotReadyError(ConflictError):
    code = "IMAGE_NOT_READY"
    default_message = "Chưa có ảnh dịch"


class ImageFileNotFoundError(NotFoundError):
    code = "FILE_NOT_FOUND"
    default_message = "Không tìm thấy tệp ảnh"


class JobNotRunningError(ConflictError):
    code = "JOB_NOT_RUNNING"
    default_message = "Công việc không còn ở trạng thái đang xử lý"


class InvalidBubbleError(InvalidInputError):
    code = "INVALID_BUBBLE"
    default_message = "Dữ liệu vùng chữ không hợp lệ"


class InvalidResultKindError(InvalidInputError):
    code = "INVALID_RESULT_KIND"
    default_message = "Chỉ lưu ảnh đã xóa chữ hoặc ảnh đã dịch"
