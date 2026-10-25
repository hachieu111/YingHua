"""Lỗi nghiệp vụ của M08 (thông điệp theo docs/modules-functions.md §4.8)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError, RateLimitedError


class CardNotFoundError(NotFoundError):
    code = "CARD_NOT_FOUND"
    default_message = "Không tìm thấy thẻ"


class InvalidRatingError(InvalidInputError):
    code = "INVALID_RATING"
    default_message = "Mức đánh giá phải là 1 (Quên), 2 (Khó), 3 (Được) hoặc 4 (Dễ)"


class InvalidDeckError(InvalidInputError):
    code = "INVALID_DECK"
    default_message = "Bộ thẻ không hợp lệ"


class CardSuspendedError(ConflictError):
    code = "CARD_SUSPENDED"
    default_message = "Thẻ đang tạm ngưng, hãy tiếp tục thẻ trước khi ôn"


class PresentationIdTakenError(ConflictError):
    code = "PRESENTATION_ID_TAKEN"
    default_message = "Mã lượt hiển thị này đã được dùng cho thẻ khác"


class AiNoteEntryNotFoundError(NotFoundError):
    """Mục từ không có hoặc của người khác (F08.11): trả lời như không tồn tại."""

    code = "VOCAB_NOT_FOUND"
    default_message = "Không tìm thấy từ trong sổ tay"


class AiNoteRegenerateLimitError(RateLimitedError):
    code = "AI_NOTE_REGENERATE_LIMIT"
    default_message = "Bạn đã hết lượt tạo lại thẻ AI cho từ này"


class AiNoteGeneratorUnavailableError(Exception):
    """Dịch vụ LLM không dùng được (tắt, lỗi mạng, quá thời gian). Không bao giờ lộ ra API: use case dùng bản
    dự phòng (F08.11)."""

    def __init__(self, reason: str = "network") -> None:
        self.reason = reason
        super().__init__(reason)
