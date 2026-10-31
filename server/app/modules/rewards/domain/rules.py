"""Quy tắc nghiệp vụ thuần của M17 (F17.01, F17.03, F17.04). Hàm nhận `now`, không đọc đồng hồ hệ thống."""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone

from app.modules.rewards.domain.entities import (
    FrameAcquireKind,
    ItemKind,
    LedgerReason,
    RewardBundle,
)
from app.modules.rewards.domain.errors import InvalidRewardError

# Giới hạn mỗi lần ghi sổ (F17.01).
MAX_COINS_PER_GRANT = 100_000
MAX_TICKETS_PER_GRANT = 10
MAX_VIP_DAYS_PER_GRANT = 365
MAX_TICKET_BALANCE = 99

WELCOME_VIP_DAYS = 3  # quà chào mừng (F17.03)
WELCOME_KEY = "welcome"
VIP_REMINDER_WINDOW = timedelta(hours=24)  # nhắc khi VIP còn dưới ngần này (F17.03, US-HG-06)
NOTE_MAX_LENGTH = 500

PRICE_MIN = 1
PRICE_MAX = 100_000
ITEM_VIP_DAYS_MAX = 365
ITEM_TICKETS_MAX = 10

ITEM_CODE_PATTERN = re.compile(r"^[a-z0-9_]{2,32}$")

# Giờ Việt Nam cố định UTC+7, dùng để viết ngày hết hạn trong thông báo.
VIETNAM_TZ = timezone(timedelta(hours=7))

_DAY = timedelta(days=1)

LEDGER_REASON_LABELS: dict[LedgerReason, str] = {
    LedgerReason.SEASON_REWARD: "Thưởng mùa thi đua",
    LedgerReason.QUEST_BONUS: "Thưởng nhiệm vụ ngày",
    LedgerReason.STREAK_MILESTONE: "Thưởng mốc chuỗi ngày",
    LedgerReason.ACHIEVEMENT: "Mở khóa huy hiệu",
    LedgerReason.WELCOME: "Quà chào mừng",
    LedgerReason.REDEMPTION: "Đổi thưởng",
    LedgerReason.VIP_UNLOCK: "Mở khóa truyện VIP",
    LedgerReason.ADMIN_ADJUST: "Điều chỉnh bởi quản trị viên",
}

# Lý do mà số vé vượt trần ví bị từ chối thay vì cắt bớt: người dùng/quản trị chủ động thao tác nên cần biết.
STRICT_TICKET_REASONS = frozenset({LedgerReason.REDEMPTION, LedgerReason.ADMIN_ADJUST})

FRAME_ACQUIRE_LABELS: dict[FrameAcquireKind, str] = {
    FrameAcquireKind.SEASON: "Thưởng mùa thi đua hoặc mục tiêu tuần",
    FrameAcquireKind.SHOP: "Đổi ở cửa hàng",
    FrameAcquireKind.VIP: "Dùng được khi đang VIP",
}


def validate_bundle(bundle: RewardBundle) -> None:
    """Kiểm giới hạn mỗi lần của F17.01 (áp dụng cho cả khoản trừ)."""
    if abs(bundle.coins) > MAX_COINS_PER_GRANT:
        raise InvalidRewardError(f"Số xu mỗi lần tối đa {MAX_COINS_PER_GRANT}")
    if abs(bundle.tickets) > MAX_TICKETS_PER_GRANT:
        raise InvalidRewardError(f"Số vé mỗi lần tối đa {MAX_TICKETS_PER_GRANT}")
    if bundle.vip_days < 0 or bundle.vip_days > MAX_VIP_DAYS_PER_GRANT:
        raise InvalidRewardError(f"Số ngày VIP mỗi lần từ 0 đến {MAX_VIP_DAYS_PER_GRANT}")
    if bundle.frame is not None and bundle.frame.days is not None and bundle.frame.days < 1:
        raise InvalidRewardError("Số ngày dùng khung phải từ 1")


def extend_vip(vip_until: datetime | None, days: int, now: datetime) -> datetime:
    """Cộng dồn: hạn mới = max(hiện tại, hạn hiện có) + số ngày (F17.03)."""
    base = vip_until if vip_until is not None and vip_until > now else now
    return base + timedelta(days=days)


def vip_days_left(vip_until: datetime | None, now: datetime) -> int:
    """Số ngày VIP còn lại, làm tròn lên (còn 3 giờ vẫn tính là 1 ngày); 0 nếu không VIP."""
    if vip_until is None or vip_until <= now:
        return 0
    return max(1, math.ceil((vip_until - now) / _DAY))


def effective_ai_limit(is_vip: bool, normal_limit: int, vip_limit: int) -> int:
    """Hạn mức AI hiệu lực (F17.04): đang VIP thì max(hạn mức VIP, hạn mức thường)."""
    return max(vip_limit, normal_limit) if is_vip else normal_limit


def clean_note(raw: str | None) -> str | None:
    value = " ".join((raw or "").split())
    return value[:NOTE_MAX_LENGTH] if value else None


def validate_item_code(raw: str) -> str:
    code = raw.strip().lower()
    if not ITEM_CODE_PATTERN.match(code):
        raise InvalidRewardError("Mã món gồm 2-32 ký tự chữ thường, số hoặc dấu gạch dưới")
    return code


def validate_item_kind_fields(
    kind: ItemKind, vip_days: int | None, ticket_count: int | None, frame_id: int | None
) -> None:
    """Chỉ trường của đúng loại món được có giá trị, và nằm trong khoảng cho phép (F17.09)."""
    present = {
        ItemKind.VIP_DAYS: vip_days,
        ItemKind.VIP_TICKET: ticket_count,
        ItemKind.AVATAR_FRAME: frame_id,
    }
    for item_kind, value in present.items():
        if (item_kind is kind) != (value is not None):
            raise InvalidRewardError("Thông tin món không khớp với loại món")
    if vip_days is not None and not 1 <= vip_days <= ITEM_VIP_DAYS_MAX:
        raise InvalidRewardError(f"Số ngày VIP của món từ 1 đến {ITEM_VIP_DAYS_MAX}")
    if ticket_count is not None and not 1 <= ticket_count <= ITEM_TICKETS_MAX:
        raise InvalidRewardError(f"Số vé của món từ 1 đến {ITEM_TICKETS_MAX}")


def validate_price(price: int) -> int:
    if not PRICE_MIN <= price <= PRICE_MAX:
        raise InvalidRewardError(f"Giá phải từ {PRICE_MIN} đến {PRICE_MAX} xu")
    return price


def format_vietnam_time(moment: datetime) -> str:
    return moment.astimezone(VIETNAM_TZ).strftime("%d/%m/%Y %H:%M")
