"""Lỗi nghiệp vụ của M07 (thông điệp theo docs/modules-functions.md §4.7)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class VocabNotFoundError(NotFoundError):
    code = "VOCAB_NOT_FOUND"
    default_message = "Không tìm thấy từ trong sổ tay"


class VocabContextNotFoundError(NotFoundError):
    code = "VOCAB_CONTEXT_NOT_FOUND"
    default_message = "Không tìm thấy ngữ cảnh của từ"


class BubbleNotFoundError(NotFoundError):
    code = "BUBBLE_NOT_FOUND"
    default_message = "Không tìm thấy vùng chữ"


class VocabContextAlreadySavedError(ConflictError):
    code = "VOCAB_CONTEXT_ALREADY_SAVED"
    default_message = "Từ này đã có với ngữ cảnh này"


class InvalidTermError(InvalidInputError):
    code = "INVALID_TERM"
    default_message = "Từ cần lưu phải là chữ Hán, tối đa 32 ký tự"


class TermNotInBubbleError(InvalidInputError):
    code = "TERM_NOT_IN_BUBBLE"
    default_message = "Từ cần lưu không nằm trong vùng chữ này"


class NoteTooLongError(InvalidInputError):
    code = "NOTE_TOO_LONG"
    default_message = "Ghi chú vượt quá số ký tự cho phép"


class InvalidVocabStatusError(InvalidInputError):
    code = "INVALID_VOCAB_STATUS"
    default_message = "Trạng thái học không hợp lệ"


class InvalidVocabSourceError(InvalidInputError):
    code = "INVALID_VOCAB_SOURCE"
    default_message = "Nguồn lưu từ không hợp lệ"


class InvalidHskFilterError(InvalidInputError):
    code = "INVALID_HSK_FILTER"
    default_message = 'Cấp HSK phải từ 1 đến 9 hoặc "none" (ngoài HSK)'


class InvalidVocabFieldError(InvalidInputError):
    code = "INVALID_VOCAB_FIELD"
    default_message = "Giá trị không hợp lệ"


class SentenceAlreadySavedError(ConflictError):
    code = "SENTENCE_ALREADY_SAVED"
    default_message = "Câu này đã được lưu"


class SavedSentenceNotFoundError(NotFoundError):
    code = "SAVED_SENTENCE_NOT_FOUND"
    default_message = "Không tìm thấy câu thoại đã lưu"


class EmptyBubbleTextError(InvalidInputError):
    code = "BUBBLE_TEXT_EMPTY"
    default_message = "Vùng chữ này không có nội dung để lưu"


class PageHasNoWordsError(InvalidInputError):
    code = "PAGE_HAS_NO_WORDS"
    default_message = "Trang chưa có từ để lưu"
