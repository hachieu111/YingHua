"""Lỗi nghiệp vụ của M16 (thông điệp tiếng Việt, mã cố định)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class AchievementNotFoundError(NotFoundError):
    code = "ACHIEVEMENT_NOT_FOUND"
    default_message = "Không tìm thấy huy hiệu"


class AchievementLockedError(ConflictError):
    code = "ACHIEVEMENT_LOCKED"
    default_message = "Huy hiệu này chưa được mở khóa"


class NotEnoughCharsForGameError(ConflictError):
    code = "NOT_ENOUGH_WORDS_FOR_GAME"
    default_message = "Chưa đủ chữ để chơi, hãy lưu thêm từ vào Sổ tay"


class UnknownRadicalError(InvalidInputError):
    code = "UNKNOWN_RADICAL"
    default_message = "Bộ thủ không hợp lệ"


class InvalidMinigameRequestError(InvalidInputError):
    code = "INVALID_MINIGAME_REQUEST"
    default_message = "Chế độ chơi cần cấp HSK (1-7) hoặc bộ thủ tương ứng"


class MinigameRoundNotFoundError(NotFoundError):
    code = "MINIGAME_ROUND_NOT_FOUND"
    default_message = "Không tìm thấy lượt chơi"


class MinigameRoundUsedError(ConflictError):
    code = "MINIGAME_ROUND_USED"
    default_message = "Lượt chơi này đã được nộp kết quả"


class MinigameRoundExpiredError(ConflictError):
    code = "MINIGAME_ROUND_EXPIRED"
    default_message = "Lượt chơi đã quá hạn nộp, hãy bắt đầu ván mới"


class InvalidMinigameResultError(InvalidInputError):
    code = "INVALID_MINIGAME_RESULT"
    default_message = "Kết quả ván chơi không hợp lệ"
