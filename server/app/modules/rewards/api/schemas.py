from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.rewards.application.dto import (
    AdminItemView,
    AiLimits,
    FrameView,
    LedgerPage,
    RedemptionResult,
    SeriesVipResult,
    ShopItemView,
    UnlockResult,
    UnlockView,
    UserRewardsView,
    VipOverview,
    VipStatus,
    WalletView,
)
from app.modules.rewards.domain.entities import AvatarFrame, LedgerEntry, RewardItem, UserFrame
from app.modules.rewards.domain.rules import (
    FRAME_ACQUIRE_LABELS,
    ITEM_TICKETS_MAX,
    ITEM_VIP_DAYS_MAX,
    LEDGER_REASON_LABELS,
    MAX_COINS_PER_GRANT,
    MAX_TICKETS_PER_GRANT,
    MAX_VIP_DAYS_PER_GRANT,
    NOTE_MAX_LENGTH,
    PRICE_MAX,
    PRICE_MIN,
)

Currency = Literal["coin", "ticket", "vip_days"]


class FrameInfo(BaseModel):
    code: str
    name: str
    style_key: str

    @classmethod
    def of(cls, frame: AvatarFrame | None) -> FrameInfo | None:
        return cls(code=frame.code, name=frame.name, style_key=frame.style_key) if frame else None


class VipStatusResponse(BaseModel):
    is_active: bool
    vip_until: datetime | None
    days_left: int

    @classmethod
    def of(cls, s: VipStatus) -> VipStatusResponse:
        return cls(is_active=s.is_active, vip_until=s.vip_until, days_left=s.days_left)


class WalletResponse(BaseModel):
    coin_balance: int
    ticket_balance: int
    vip: VipStatusResponse
    equipped_frame: FrameInfo | None

    @classmethod
    def of(cls, w: WalletView) -> WalletResponse:
        return cls(
            coin_balance=w.coin_balance,
            ticket_balance=w.ticket_balance,
            vip=VipStatusResponse.of(w.vip),
            equipped_frame=FrameInfo.of(w.equipped_frame),
        )


class LedgerEntryResponse(BaseModel):
    id: int
    currency: Currency
    amount: int = Field(description="Dương là nhận, âm là tiêu hoặc thu")
    balance_after: int | None
    vip_until_after: datetime | None
    reason: str
    reason_label: str = Field(description="Nhãn tiếng Việt của lý do")
    note: str | None
    created_at: datetime

    @classmethod
    def of(cls, e: LedgerEntry) -> LedgerEntryResponse:
        return cls(
            id=e.id,
            currency=e.currency.value,
            amount=e.amount,
            balance_after=e.balance_after,
            vip_until_after=e.vip_until_after,
            reason=e.reason.value,
            reason_label=LEDGER_REASON_LABELS[e.reason],
            note=e.note,
            created_at=e.created_at,
        )


class LedgerPageResponse(BaseModel):
    items: list[LedgerEntryResponse]
    total: int
    page: int
    size: int

    @classmethod
    def of(cls, p: LedgerPage, page: int, size: int) -> LedgerPageResponse:
        return cls(items=[LedgerEntryResponse.of(e) for e in p.items], total=p.total, page=page, size=size)


class AdminLedgerEntryResponse(LedgerEntryResponse):
    actor_id: int | None = Field(description="Quản trị viên thực hiện; null với phần thưởng tự động")

    @classmethod
    def of_admin(cls, e: LedgerEntry) -> AdminLedgerEntryResponse:
        return cls(**LedgerEntryResponse.of(e).model_dump(), actor_id=e.actor_id)


class AdminLedgerPageResponse(BaseModel):
    items: list[AdminLedgerEntryResponse]
    total: int
    page: int
    size: int


class AiLimitsResponse(BaseModel):
    quiz_daily_llm_limit: int
    ai_note_daily_limit: int
    grammar_daily_limit: int
    mistake_review_daily_limit: int

    @classmethod
    def of(cls, a: AiLimits) -> AiLimitsResponse:
        return cls(
            quiz_daily_llm_limit=a.quiz_daily_llm_limit,
            ai_note_daily_limit=a.ai_note_daily_limit,
            grammar_daily_limit=a.grammar_daily_limit,
            mistake_review_daily_limit=a.mistake_review_daily_limit,
        )


class VipOverviewResponse(BaseModel):
    is_active: bool
    vip_until: datetime | None
    days_left: int
    ai_limits: AiLimitsResponse
    can_read_vip_series: bool
    can_use_vip_frame: bool
    unlocked_series_count: int

    @classmethod
    def of(cls, o: VipOverview) -> VipOverviewResponse:
        return cls(
            is_active=o.status.is_active,
            vip_until=o.status.vip_until,
            days_left=o.status.days_left,
            ai_limits=AiLimitsResponse.of(o.ai_limits),
            can_read_vip_series=o.can_read_vip_series,
            can_use_vip_frame=o.can_use_vip_frame,
            unlocked_series_count=o.unlocked_series_count,
        )


class UnlockRequest(BaseModel):
    series_id: int = Field(ge=1)
    request_id: uuid.UUID = Field(description="UUID do trình duyệt sinh, chống bấm đúp")


class UnlockResponse(BaseModel):
    series_id: int
    unlocked_at: datetime
    tickets_left: int

    @classmethod
    def of(cls, r: UnlockResult) -> UnlockResponse:
        return cls(
            series_id=r.unlock.series_id, unlocked_at=r.unlock.unlocked_at, tickets_left=r.tickets_left
        )


class UnlockItemResponse(BaseModel):
    series_id: int
    series_title: str | None
    unlocked_at: datetime
    source: str

    @classmethod
    def of(cls, u: UnlockView) -> UnlockItemResponse:
        return cls(
            series_id=u.unlock.series_id,
            series_title=u.series_title,
            unlocked_at=u.unlock.unlocked_at,
            source=u.unlock.source.value,
        )


class ShopItemResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    kind: str
    price_coins: int
    vip_days: int | None
    ticket_count: int | None
    frame: FrameInfo | None
    per_user_limit: int | None
    remaining: int | None = Field(description="Số lượt đổi còn lại của người gọi; null = không giới hạn")
    owned: bool = Field(description="Đã sở hữu vĩnh viễn khung của món này")
    affordable: bool = Field(description="Đủ xu để đổi")

    @classmethod
    def of(cls, v: ShopItemView) -> ShopItemResponse:
        i = v.item
        return cls(
            id=i.id,
            code=i.code,
            name=i.name,
            description=i.description,
            kind=i.kind.value,
            price_coins=i.price_coins,
            vip_days=i.vip_days,
            ticket_count=i.ticket_count,
            frame=FrameInfo.of(v.frame),
            per_user_limit=i.per_user_limit,
            remaining=v.remaining,
            owned=v.owned,
            affordable=v.affordable,
        )


class RedeemRequest(BaseModel):
    item_id: int = Field(ge=1)
    request_id: uuid.UUID = Field(description="UUID do trình duyệt sinh, chống bấm đúp")


class RedemptionResponse(BaseModel):
    id: int
    item_id: int
    item_code: str
    item_name: str
    price_coins: int = Field(description="Giá tại thời điểm đổi")
    created_at: datetime
    wallet: WalletResponse

    @classmethod
    def of(cls, r: RedemptionResult) -> RedemptionResponse:
        return cls(
            id=r.redemption.id,
            item_id=r.item.id,
            item_code=r.item.code,
            item_name=r.item.name,
            price_coins=r.redemption.price_coins,
            created_at=r.redemption.created_at,
            wallet=WalletResponse.of(r.wallet),
        )


class AdminFrameResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    style_key: str
    acquire_kind: str
    acquire_label: str = Field(description="Cách kiếm khung bằng tiếng Việt")

    @classmethod
    def of(cls, f: AvatarFrame) -> AdminFrameResponse:
        return cls(
            id=f.id,
            code=f.code,
            name=f.name,
            description=f.description,
            style_key=f.style_key,
            acquire_kind=f.acquire_kind.value,
            acquire_label=FRAME_ACQUIRE_LABELS[f.acquire_kind],
        )


class FrameResponse(BaseModel):
    code: str
    name: str
    description: str | None
    style_key: str
    acquire_kind: str
    acquire_label: str = Field(description="Cách kiếm khung bằng tiếng Việt")
    owned: bool
    expires_at: datetime | None
    equippable: bool
    equipped: bool

    @classmethod
    def of(cls, v: FrameView) -> FrameResponse:
        f = v.frame
        return cls(
            code=f.code,
            name=f.name,
            description=f.description,
            style_key=f.style_key,
            acquire_kind=f.acquire_kind.value,
            acquire_label=FRAME_ACQUIRE_LABELS[f.acquire_kind],
            owned=v.owned,
            expires_at=v.expires_at,
            equippable=v.equippable,
            equipped=v.equipped,
        )


class EquipFrameRequest(BaseModel):
    frame_code: str | None = Field(default=None, max_length=32, description="null để tháo khung")


class EquippedFrameResponse(BaseModel):
    equipped_frame: FrameInfo | None


# --- Quản trị -----------------------------------------------------------------------------------


class SeriesVipRequest(BaseModel):
    is_vip: bool


class SeriesVipResponse(BaseModel):
    series_id: int
    is_vip: bool
    has_trial_chapter: bool
    warning: str | None = Field(description="Cảnh báo khi truyện VIP chưa có chương đọc thử")

    @classmethod
    def of(cls, r: SeriesVipResult) -> SeriesVipResponse:
        return cls(
            series_id=r.series_id, is_vip=r.is_vip, has_trial_chapter=r.has_trial_chapter, warning=r.warning
        )


class RewardItemResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    kind: str
    price_coins: int
    vip_days: int | None
    ticket_count: int | None
    frame: FrameInfo | None
    per_user_limit: int | None
    is_active: bool
    sort_order: int
    has_redemptions: bool = Field(description="Đã có lượt đổi: không đổi được loại và đối tượng")
    updated_at: datetime

    @classmethod
    def of(cls, v: AdminItemView) -> RewardItemResponse:
        i: RewardItem = v.item
        return cls(
            id=i.id,
            code=i.code,
            name=i.name,
            description=i.description,
            kind=i.kind.value,
            price_coins=i.price_coins,
            vip_days=i.vip_days,
            ticket_count=i.ticket_count,
            frame=FrameInfo.of(v.frame),
            per_user_limit=i.per_user_limit,
            is_active=i.is_active,
            sort_order=i.sort_order,
            has_redemptions=v.redemption_count_locked,
            updated_at=i.updated_at,
        )


class CreateRewardItemRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    kind: Literal["vip_days", "vip_ticket", "avatar_frame"]
    price_coins: int = Field(ge=PRICE_MIN, le=PRICE_MAX)
    vip_days: int | None = Field(default=None, ge=1, le=ITEM_VIP_DAYS_MAX)
    ticket_count: int | None = Field(default=None, ge=1, le=ITEM_TICKETS_MAX)
    frame_code: str | None = Field(default=None, max_length=32)
    per_user_limit: int | None = Field(default=None, ge=1, le=32767)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=-32768, le=32767)


class UpdateRewardItemRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    price_coins: int | None = Field(default=None, ge=PRICE_MIN, le=PRICE_MAX)
    vip_days: int | None = Field(default=None, ge=1, le=ITEM_VIP_DAYS_MAX)
    ticket_count: int | None = Field(default=None, ge=1, le=ITEM_TICKETS_MAX)
    frame_code: str | None = Field(default=None, max_length=32)
    per_user_limit: int | None = Field(default=None, ge=1, le=32767)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=-32768, le=32767)


class VipGrantRequest(BaseModel):
    days: int | None = Field(default=None, ge=1, le=MAX_VIP_DAYS_PER_GRANT)
    revoke: bool = False
    reason: str = Field(min_length=1, max_length=NOTE_MAX_LENGTH)
    request_id: uuid.UUID = Field(description="UUID do trình duyệt sinh, chống bấm đúp")


class WalletAdjustRequest(BaseModel):
    currency: Literal["coin", "ticket"]
    amount: int = Field(ge=-MAX_COINS_PER_GRANT, le=MAX_COINS_PER_GRANT)
    reason: str = Field(min_length=1, max_length=NOTE_MAX_LENGTH)
    request_id: uuid.UUID = Field(description="UUID do trình duyệt sinh, chống bấm đúp")

    @model_validator(mode="after")
    def _check_amount(self) -> WalletAdjustRequest:
        if self.amount == 0:
            raise ValueError("Số lượng điều chỉnh phải khác 0")
        if self.currency == "ticket" and abs(self.amount) > MAX_TICKETS_PER_GRANT:
            raise ValueError(f"Số vé mỗi lần tối đa {MAX_TICKETS_PER_GRANT}")
        return self


class UserFrameResponse(BaseModel):
    code: str
    name: str
    source: str
    acquired_at: datetime
    expires_at: datetime | None

    @classmethod
    def of(cls, frame: AvatarFrame, owned: UserFrame) -> UserFrameResponse:
        return cls(
            code=frame.code,
            name=frame.name,
            source=owned.source.value,
            acquired_at=owned.acquired_at,
            expires_at=owned.expires_at,
        )


class UserRewardsResponse(BaseModel):
    wallet: WalletResponse
    unlocks: list[UnlockItemResponse]
    frames: list[UserFrameResponse]
    ledger: AdminLedgerPageResponse

    @classmethod
    def of(cls, v: UserRewardsView, page: int, size: int) -> UserRewardsResponse:
        return cls(
            wallet=WalletResponse.of(v.wallet),
            unlocks=[UnlockItemResponse.of(u) for u in v.unlocks],
            frames=[UserFrameResponse.of(f, o) for f, o in v.frames],
            ledger=AdminLedgerPageResponse(
                items=[AdminLedgerEntryResponse.of_admin(e) for e in v.ledger.items],
                total=v.ledger.total,
                page=page,
                size=size,
            ),
        )
