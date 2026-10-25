from __future__ import annotations

from app.core.errors import ExternalServiceError, InvalidInputError, PayloadTooLargeError, RateLimitedError
from app.modules.tts.domain.value_objects import CallStatus


class TtsTextEmptyError(InvalidInputError):
    code = "TTS_TEXT_EMPTY"
    default_message = "Chưa có nội dung để phát âm"


class TtsTextTooLongError(PayloadTooLargeError):
    code = "TTS_TEXT_TOO_LONG"
    default_message = "Nội dung quá dài để phát âm"


class TtsRateLimitedError(RateLimitedError):
    code = "TTS_RATE_LIMITED"
    default_message = "Bạn nghe thử quá nhiều lần, hãy đăng nhập hoặc thử lại sau"


class TtsDisabledError(ExternalServiceError):
    code = "TTS_DISABLED"
    default_message = "Tính năng phát âm đang tạm tắt"


class TtsUnavailableError(ExternalServiceError):
    """Dịch vụ TTS lỗi/hết thời gian/trả âm thanh hỏng (F11.06). Thông điệp an toàn cho người dùng."""

    code = "TTS_UNAVAILABLE"
    default_message = "Không phát được âm thanh, thử lại sau"

    def __init__(self, failure: CallStatus = CallStatus.ERROR, reason: str = "UNKNOWN") -> None:
        super().__init__()
        self.failure = failure
        self.reason = reason  # mã ngắn để ghi nhật ký; không chứa nội dung văn bản
