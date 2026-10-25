"""Lỗi nghiệp vụ của M10 (docs/modules-functions.md §4.10)."""

from __future__ import annotations

from app.core.errors import InvalidInputError, NotFoundError


class InvalidSuggestionTermError(InvalidInputError):
    code = "INVALID_TERM"
    default_message = "Từ phải là chữ Hán, tối đa 32 ký tự"


class SuggestionNotFoundError(NotFoundError):
    code = "SUGGESTION_NOT_FOUND"
    default_message = "Từ này không xuất hiện trong chương"
