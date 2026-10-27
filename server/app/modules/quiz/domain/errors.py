"""Lỗi nghiệp vụ của M09 (thông điệp theo docs/modules-functions.md §4.9)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class QuizNotFoundError(NotFoundError):
    code = "QUIZ_NOT_FOUND"
    default_message = "Không tìm thấy bài kiểm tra"


class NotEnoughWordsForQuizError(InvalidInputError):
    code = "NOT_ENOUGH_WORDS_FOR_QUIZ"
    default_message = "Cần tối thiểu 10 từ trong Sổ tay cá nhân"


class QuizAlreadySubmittedError(ConflictError):
    code = "QUIZ_ALREADY_SUBMITTED"
    default_message = "Bài kiểm tra này đã được nộp"


class InvalidQuestionCountError(InvalidInputError):
    code = "INVALID_QUESTION_COUNT"
    default_message = "Số câu phải từ 5 đến 20"


class InvalidQuizAnswersError(InvalidInputError):
    code = "INVALID_QUIZ_ANSWERS"
    default_message = "Đáp án gửi lên không khớp với các câu của bài"


class QuizGeneratorUnavailableError(Exception):
    """Dịch vụ sinh đề (LLM) không dùng được: tắt, lỗi mạng, hết hạn mức... Không bao giờ lộ ra API.

    `reason` là một giá trị của `FallbackReason`; use case chuyển sang đề dự phòng (F09.08).
    """

    def __init__(self, reason: str = "network", message: str = "Dịch vụ sinh đề không khả dụng") -> None:
        self.reason = reason
        super().__init__(message)


class QuizQuestionNotFoundError(NotFoundError):
    code = "QUIZ_QUESTION_NOT_FOUND"
    default_message = "Không tìm thấy câu hỏi trong bài kiểm tra"


class QuizNotSubmittedError(ConflictError):
    code = "QUIZ_NOT_SUBMITTED"
    default_message = "Hãy nộp bài trước khi lưu từ"


class QuestionNotWrongError(InvalidInputError):
    code = "QUESTION_NOT_WRONG"
    default_message = "Chỉ xem được giải thích lỗi sai của câu đã làm sai"


class MistakePracticeNotFoundError(NotFoundError):
    code = "MISTAKE_PRACTICE_NOT_FOUND"
    default_message = "Câu này chưa có câu luyện thêm"


class InvalidPracticeChoiceError(InvalidInputError):
    code = "INVALID_PRACTICE_CHOICE"
    default_message = "Lựa chọn không nằm trong các phương án của câu luyện"


class WordNotSavableError(InvalidInputError):
    code = "WORD_NOT_SAVABLE"
    default_message = "Chỉ lưu được từ mở rộng; từ đã lưu đã có trong sổ tay"
