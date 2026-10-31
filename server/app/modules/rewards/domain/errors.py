"""Lỗi nghiệp vụ của M17 (mã và thông điệp theo docs/modules-functions.md §4.17)."""

from __future__ import annotations

from app.core.errors import ConflictError, InvalidInputError, NotFoundError


class NotEnoughCoinsError(ConflictError):
    code = "NOT_ENOUGH_COINS"
    default_message = "Bạn không đủ xu Sakura"


class NotEnoughTicketsError(ConflictError):
    code = "NOT_ENOUGH_TICKETS"
    default_message = "Bạn không còn vé đọc truyện VIP"


class TicketLimitReachedError(ConflictError):
    code = "TICKET_LIMIT_REACHED"
    default_message = "Ví chỉ chứa tối đa 99 vé đọc truyện VIP"


class WalletNegativeError(ConflictError):
    code = "WALLET_NEGATIVE"
    default_message = "Kết quả điều chỉnh làm số dư bị âm"


class VipNotActiveError(ConflictError):
    code = "VIP_NOT_ACTIVE"
    default_message = "Người dùng này hiện không có VIP"


class InvalidRewardError(InvalidInputError):
    code = "INVALID_REWARD"
    default_message = "Phần thưởng không hợp lệ"


class VipSeriesNotFoundError(NotFoundError):
    code = "SERIES_NOT_FOUND"
    default_message = "Không tìm thấy truyện"


class SeriesNotVipError(ConflictError):
    code = "SERIES_NOT_VIP"
    default_message = "Truyện này không phải truyện VIP"


class SeriesAlreadyUnlockedError(ConflictError):
    code = "SERIES_ALREADY_UNLOCKED"
    default_message = "Bạn đã mở khóa truyện này rồi"


class SeriesNotPublicError(ConflictError):
    code = "SERIES_NOT_PUBLIC"
    default_message = "Chỉ truyện công khai mới đặt được cờ VIP"


class RequestReusedError(ConflictError):
    code = "REQUEST_ID_REUSED"
    default_message = "Mã yêu cầu này đã được dùng cho một thao tác khác"


class RewardItemUnavailableError(NotFoundError):
    code = "REWARD_ITEM_UNAVAILABLE"
    default_message = "Món đổi thưởng đã ngừng bán hoặc không tồn tại"


class FrameAlreadyOwnedError(ConflictError):
    code = "FRAME_ALREADY_OWNED"
    default_message = "Bạn đã sở hữu khung này"


class RewardLimitReachedError(ConflictError):
    code = "REWARD_LIMIT_REACHED"
    default_message = "Bạn đã đổi món này đủ số lần cho phép"


class FrameNotAvailableError(ConflictError):
    code = "FRAME_NOT_AVAILABLE"
    default_message = "Bạn chưa có khung này hoặc khung đã hết hạn"


class RewardItemNotFoundError(NotFoundError):
    code = "REWARD_ITEM_NOT_FOUND"
    default_message = "Không tìm thấy món đổi thưởng"


class RewardItemCodeTakenError(ConflictError):
    code = "REWARD_ITEM_CODE_TAKEN"
    default_message = "Mã món đổi thưởng đã tồn tại"


class RewardItemLockedError(ConflictError):
    code = "REWARD_ITEM_LOCKED"
    default_message = "Món đã có lượt đổi nên không đổi được loại và đối tượng, chỉ ngừng bán được"
