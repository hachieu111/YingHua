from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class SelfDemoteError(InvalidInputError):
    code = "SELF_DEMOTE"
    default_message = "Không thể tự hạ quyền chính mình"


class SelfLockError(InvalidInputError):
    code = "SELF_LOCK"
    default_message = "Không thể tự khóa chính mình"


class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"
    default_message = "Không tìm thấy người dùng"


class UnknownSettingError(InvalidInputError):
    code = "UNKNOWN_SETTING"
    default_message = "Khóa cấu hình không tồn tại"


class InvalidSettingValueError(InvalidInputError):
    code = "INVALID_SETTING_VALUE"
    default_message = "Giá trị cấu hình không hợp lệ"


class EmptySettingsChangeError(InvalidInputError):
    code = "EMPTY_SETTINGS_CHANGE"
    default_message = "Chưa có cấu hình nào cần thay đổi"


class SamplePageInvalidError(InvalidInputError):
    code = "SAMPLE_PAGE_INVALID"
    default_message = "Trang mẫu phải là trang đã dịch xong của một truyện công khai"


class RemovalReasonRequiredError(InvalidInputError):
    code = "REMOVAL_REASON_REQUIRED"
    default_message = "Cần nhập lý do gỡ ảnh"


class RemovalTargetInvalidError(InvalidInputError):
    code = "REMOVAL_TARGET_INVALID"
    default_message = "Chỉ định đúng một trong hai: mã trang hoặc mã tệp ảnh"


class RemovalTargetNotFoundError(NotFoundError):
    code = "REMOVAL_TARGET_NOT_FOUND"
    default_message = "Không tìm thấy ảnh hoặc trang cần gỡ"


class AlreadyRemovedError(ConflictError):
    code = "ALREADY_REMOVED"
    default_message = "Ảnh này đã được gỡ trước đó"
