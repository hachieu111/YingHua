"""DTO của M17."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.modules.rewards.domain.entities import (
    AvatarFrame,
    Currency,
    LedgerEntry,
    LedgerReason,
    Redemption,
    RewardBundle,
    RewardItem,
    UserFrame,
    VipUnlock,
)


@dataclass(frozen=True, slots=True)
class GrantCommand:
    """F17.01 - một lần ghi sổ phần thưởng (hoặc khoản trừ).

    `key` là khóa chống trùng: gọi lại cùng khóa thì loại đã ghi bị bỏ qua. `reason` bắt buộc khi gói có xu,
    vé hoặc ngày VIP; gói chỉ có khung thì không ghi sổ nên bỏ trống được.
    """

    user_id: int
    bundle: RewardBundle
    key: str
    reason: LedgerReason | None = None
    actor_id: int | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class WalletSnapshot:
    user_id: int
    coin_balance: int
    ticket_balance: int
    vip_until: datetime | None
    equipped_frame_id: int | None


@dataclass(frozen=True, slots=True)
class GrantResult:
    wallet: WalletSnapshot
    entries: list[LedgerEntry] = field(default_factory=list)
    duplicate: bool = False  # mọi loại của gói đã được ghi trước đó nên không làm gì
    frame: UserFrame | None = None


@dataclass(frozen=True, slots=True)
class VipStatus:
    is_active: bool
    vip_until: datetime | None
    days_left: int


@dataclass(frozen=True, slots=True)
class FrameView:
    """Khung kèm trạng thái của một người (F17.08)."""

    frame: AvatarFrame
    owned: bool  # sở hữu còn hạn, hoặc khung VIP khi đang VIP
    expires_at: datetime | None
    equippable: bool
    equipped: bool


@dataclass(frozen=True, slots=True)
class WalletView:
    coin_balance: int
    ticket_balance: int
    vip: VipStatus
    equipped_frame: AvatarFrame | None  # chỉ khi còn hiệu lực


@dataclass(frozen=True, slots=True)
class LedgerPage:
    items: list[LedgerEntry]
    total: int


@dataclass(frozen=True, slots=True)
class AiLimits:
    quiz_daily_llm_limit: int
    ai_note_daily_limit: int
    grammar_daily_limit: int
    mistake_review_daily_limit: int


@dataclass(frozen=True, slots=True)
class VipOverview:
    """F17.03 - `GET /vip/me`."""

    status: VipStatus
    ai_limits: AiLimits
    can_read_vip_series: bool
    can_use_vip_frame: bool
    unlocked_series_count: int


@dataclass(frozen=True, slots=True)
class UnlockView:
    unlock: VipUnlock
    series_title: str | None


@dataclass(frozen=True, slots=True)
class UnlockResult:
    unlock: VipUnlock
    tickets_left: int


@dataclass(frozen=True, slots=True)
class ShopItemView:
    item: RewardItem
    frame: AvatarFrame | None
    remaining: int | None  # số lượt còn lại của người gọi; None = không giới hạn
    owned: bool  # khung đã sở hữu vĩnh viễn
    affordable: bool


@dataclass(frozen=True, slots=True)
class RedemptionResult:
    redemption: Redemption
    item: RewardItem
    wallet: WalletView


@dataclass(frozen=True, slots=True)
class SeriesVipResult:
    series_id: int
    is_vip: bool
    has_trial_chapter: bool

    @property
    def warning(self) -> str | None:
        if self.is_vip and not self.has_trial_chapter:
            return "Truyện chưa có chương đọc thử"
        return None


@dataclass(frozen=True, slots=True)
class CreateItemCommand:
    code: str
    name: str
    kind: str
    price_coins: int
    description: str | None = None
    vip_days: int | None = None
    ticket_count: int | None = None
    frame_code: str | None = None
    per_user_limit: int | None = None
    is_active: bool = True
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class AdminItemView:
    item: RewardItem
    frame: AvatarFrame | None
    redemption_count_locked: bool  # đã có lượt đổi: không đổi được đối tượng


@dataclass(frozen=True, slots=True)
class UserRewardsView:
    """F17.10 - ví, VIP, mở khóa, khung và sổ của một người dùng."""

    wallet: WalletView
    unlocks: list[UnlockView]
    frames: list[tuple[AvatarFrame, UserFrame]]
    ledger: LedgerPage


@dataclass(frozen=True, slots=True)
class VipGrantCommand:
    user_id: int
    reason: str
    days: int | None = None
    revoke: bool = False
    # F17.10: mã yêu cầu do trình duyệt sinh, chống bấm đúp; API bắt buộc gửi, mặc định chỉ tiện cho test.
    request_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True, slots=True)
class WalletAdjustCommand:
    user_id: int
    currency: Currency
    amount: int
    reason: str
    request_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True, slots=True)
class RedeemCommand:
    item_id: int
    request_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class VipReminderReport:
    scanned: int = 0
    reminded: int = 0
    failed: int = 0

    def as_summary(self) -> dict[str, int]:
        return {"scanned": self.scanned, "reminded": self.reminded, "failed": self.failed}
