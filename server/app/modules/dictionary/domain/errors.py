from __future__ import annotations

from app.core.errors import InvalidInputError


class EmptyQueryError(InvalidInputError):
    code = "EMPTY_QUERY"
    default_message = "Vui lòng nhập từ khóa"


class NotChineseTextError(InvalidInputError):
    code = "NOT_CHINESE_TEXT"
    default_message = "Chỉ tra được từ tiếng Trung (chữ Hán)"


class InvalidCharacterError(InvalidInputError):
    code = "INVALID_CHARACTER"
    default_message = "Ký tự không hợp lệ, chỉ phân rã được chữ Hán"


class TextTooLongError(InvalidInputError):
    code = "TEXT_TOO_LONG"
    default_message = "Nội dung quá dài"


class DictionaryFileError(InvalidInputError):
    code = "DICTIONARY_FILE_INVALID"
    default_message = "Tệp không đọc được hoặc sai định dạng"
