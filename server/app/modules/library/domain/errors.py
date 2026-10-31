"""Lỗi nghiệp vụ của M03 (thông điệp theo docs/modules-functions.md §4.3)."""

from __future__ import annotations

from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)


class SeriesNotFoundError(NotFoundError):
    code = "SERIES_NOT_FOUND"
    default_message = "Không tìm thấy truyện"


class ChapterNotFoundError(NotFoundError):
    code = "CHAPTER_NOT_FOUND"
    default_message = "Không tìm thấy chương"


class PageNotFoundError(NotFoundError):
    code = "PAGE_NOT_FOUND"
    default_message = "Không tìm thấy trang"


class FileNotFoundForUserError(NotFoundError):
    code = "FILE_NOT_FOUND"
    default_message = "Không tìm thấy tệp"


class FileExpiredError(NotFoundError):
    code = "FILE_EXPIRED"
    default_message = "Ảnh đã hết hạn lưu"


class PageAlreadyExistsError(ConflictError):
    code = "PAGE_ALREADY_EXISTS"
    default_message = "Ảnh đã tồn tại"


class SeriesTitleDuplicateError(ConflictError):
    code = "SERIES_TITLE_DUPLICATE"
    default_message = "Bạn đã có truyện trùng tên, gửi lại với xác nhận nếu vẫn muốn tạo"


class ChapterNumberTakenError(ConflictError):
    code = "CHAPTER_NUMBER_TAKEN"
    default_message = "Số chương này đã tồn tại trong truyện"


class PublishRequiresAdminError(PermissionDeniedError):
    code = "PUBLISH_REQUIRES_ADMIN"
    default_message = "Chỉ quản trị viên được đăng truyện công khai hoặc bật đọc thử"


class LoginRequiredError(UnauthenticatedError):
    code = "LOGIN_REQUIRED"
    default_message = "Vui lòng đăng ký hoặc đăng nhập để đọc tiếp"


class VipRequiredError(PermissionDeniedError):
    """Chương của truyện VIP cần VIP còn hạn hoặc vé đã mở khóa truyện (F17.05); `details` có lối mở khóa."""

    code = "VIP_REQUIRED"
    default_message = "Chương này cần VIP hoặc vé mở khóa truyện để đọc"


class SeriesTitleRequiredError(InvalidInputError):
    code = "SERIES_TITLE_REQUIRED"
    default_message = "Tên truyện là trường bắt buộc"


class InvalidGenreError(InvalidInputError):
    code = "INVALID_GENRE"
    default_message = "Thể loại không hợp lệ"


class InvalidPageNumberError(InvalidInputError):
    code = "INVALID_PAGE_NUMBER"
    default_message = "Trang không tồn tại trong chương"


class TooManyFilesError(InvalidInputError):
    code = "TOO_MANY_FILES"
    default_message = "Mỗi lần tải lên tối đa 20 ảnh, mỗi ảnh không quá 10 MB"


class InvalidRatingError(InvalidInputError):
    code = "INVALID_RATING"
    default_message = "Số sao phải từ 1 đến 5"
