from __future__ import annotations

from app.core.errors import InvalidInputError, NotFoundError


class SelfDemoteError(InvalidInputError):
    code = "SELF_DEMOTE"
    default_message = "Không thể tự hạ quyền chính mình"


class SelfLockError(InvalidInputError):
    code = "SELF_LOCK"
    default_message = "Không thể tự khóa chính mình"


class UserNotFoundError(NotFoundError):
    code = "USER_NOT_FOUND"
    default_message = "Không tìm thấy người dùng"
