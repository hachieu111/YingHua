"""Router M17 VIP & Phần thưởng: người học (`/rewards`, `/vip`) và quản trị (`/admin/...`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, get_identity, require_admin
from app.modules.rewards.api.dependencies import RewardsServices, get_rewards_services
from app.modules.rewards.api.schemas import (
    AdminFrameResponse,
    CreateRewardItemRequest,
    EquipFrameRequest,
    EquippedFrameResponse,
    FrameInfo,
    FrameResponse,
    LedgerPageResponse,
    RedeemRequest,
    RedemptionResponse,
    RewardItemResponse,
    SeriesVipRequest,
    SeriesVipResponse,
    ShopItemResponse,
    UnlockItemResponse,
    UnlockRequest,
    UnlockResponse,
    UpdateRewardItemRequest,
    UserRewardsResponse,
    VipGrantRequest,
    VipOverviewResponse,
    WalletAdjustRequest,
    WalletResponse,
)
from app.modules.rewards.application.dto import (
    CreateItemCommand,
    RedeemCommand,
    VipGrantCommand,
    WalletAdjustCommand,
)
from app.modules.rewards.domain.entities import Currency

TAG = "M17 VIP & Phần thưởng"
rewards_router = APIRouter(prefix="/rewards", tags=[TAG])
vip_router = APIRouter(prefix="/vip", tags=[TAG])
admin_router = APIRouter(prefix="/admin", tags=[TAG])
admin_users_router = APIRouter(prefix="/admin/users/{user_id}", tags=[TAG])


@rewards_router.get("/wallet", response_model=WalletResponse, summary="Xem ví xu, vé và VIP (F17.02)")
async def get_wallet(
    identity: Identity = Depends(get_identity), services: RewardsServices = Depends(get_rewards_services)
) -> WalletResponse:
    return WalletResponse.of(await services.get_wallet.execute(identity))


@rewards_router.get(
    "/wallet/ledger", response_model=LedgerPageResponse, summary="Lịch sử nhận và tiêu của ví (F17.02)"
)
async def list_ledger(
    currency: str | None = Query(default=None, pattern="^(coin|ticket|vip_days)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: RewardsServices = Depends(get_rewards_services),
) -> LedgerPageResponse:
    flt = Currency(currency) if currency else None
    return LedgerPageResponse.of(await services.list_ledger.execute(identity, flt, page, size), page, size)


@rewards_router.get(
    "/shop/items",
    response_model=list[ShopItemResponse],
    summary="Các món đang bán ở cửa hàng đổi thưởng (F17.07)",
)
async def list_shop_items(
    identity: Identity = Depends(get_identity), services: RewardsServices = Depends(get_rewards_services)
) -> list[ShopItemResponse]:
    return [ShopItemResponse.of(v) for v in await services.list_shop.execute(identity)]


@rewards_router.post(
    "/redemptions",
    response_model=RedemptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đổi xu lấy món ở cửa hàng (F17.07)",
)
async def redeem_item(
    body: RedeemRequest,
    identity: Identity = Depends(get_identity),
    services: RewardsServices = Depends(get_rewards_services),
) -> RedemptionResponse:
    result = await services.redeem.execute(identity, RedeemCommand(body.item_id, body.request_id))
    return RedemptionResponse.of(result)


@rewards_router.get("/frames", response_model=list[FrameResponse], summary="Danh sách khung avatar (F17.08)")
async def list_frames(
    identity: Identity = Depends(get_identity), services: RewardsServices = Depends(get_rewards_services)
) -> list[FrameResponse]:
    return [FrameResponse.of(v) for v in await services.list_frames.execute(identity)]


@rewards_router.put(
    "/frames/equipped", response_model=EquippedFrameResponse, summary="Đeo hoặc tháo khung avatar (F17.08)"
)
async def equip_frame(
    body: EquipFrameRequest,
    identity: Identity = Depends(get_identity),
    services: RewardsServices = Depends(get_rewards_services),
) -> EquippedFrameResponse:
    frame = await services.equip_frame.execute(identity, body.frame_code)
    return EquippedFrameResponse(equipped_frame=FrameInfo.of(frame))


@vip_router.get(
    "/me", response_model=VipOverviewResponse, summary="Trạng thái và quyền lợi VIP của tôi (F17.03)"
)
async def get_vip_me(
    identity: Identity = Depends(get_identity), services: RewardsServices = Depends(get_rewards_services)
) -> VipOverviewResponse:
    return VipOverviewResponse.of(await services.vip_overview.execute(identity))


@vip_router.post(
    "/unlocks",
    response_model=UnlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dùng vé mở khóa vĩnh viễn một truyện VIP (F17.06)",
)
async def unlock_series(
    body: UnlockRequest,
    identity: Identity = Depends(get_identity),
    services: RewardsServices = Depends(get_rewards_services),
) -> UnlockResponse:
    return UnlockResponse.of(await services.unlock_series.execute(identity, body.series_id, body.request_id))


@vip_router.get(
    "/unlocks", response_model=list[UnlockItemResponse], summary="Các truyện VIP tôi đã mở khóa (F17.06)"
)
async def list_unlocks(
    identity: Identity = Depends(get_identity), services: RewardsServices = Depends(get_rewards_services)
) -> list[UnlockItemResponse]:
    return [UnlockItemResponse.of(u) for u in await services.list_unlocks.execute(identity)]


@admin_router.put(
    "/series/{series_id}/vip",
    response_model=SeriesVipResponse,
    summary="Quản trị: đặt hoặc bỏ cờ VIP của truyện công khai (F17.09)",
)
async def set_series_vip(
    series_id: int,
    body: SeriesVipRequest,
    admin: Identity = Depends(require_admin),
    services: RewardsServices = Depends(get_rewards_services),
) -> SeriesVipResponse:
    return SeriesVipResponse.of(await services.set_series_vip.execute(admin, series_id, body.is_vip))


@admin_router.get(
    "/reward-items",
    response_model=list[RewardItemResponse],
    summary="Quản trị: danh mục đổi thưởng đầy đủ (F17.09)",
)
async def list_reward_items(
    admin: Identity = Depends(require_admin), services: RewardsServices = Depends(get_rewards_services)
) -> list[RewardItemResponse]:
    return [RewardItemResponse.of(v) for v in await services.list_items.execute(admin)]


@admin_router.get(
    "/avatar-frames",
    response_model=list[AdminFrameResponse],
    summary="Quản trị: danh sách khung avatar cho form món đổi thưởng (F17.09)",
)
async def list_avatar_frames(
    admin: Identity = Depends(require_admin), services: RewardsServices = Depends(get_rewards_services)
) -> list[AdminFrameResponse]:
    return [AdminFrameResponse.of(f) for f in await services.list_admin_frames.execute(admin)]


@admin_router.post(
    "/reward-items",
    response_model=RewardItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Quản trị: thêm món đổi thưởng (F17.09)",
)
async def create_reward_item(
    body: CreateRewardItemRequest,
    admin: Identity = Depends(require_admin),
    services: RewardsServices = Depends(get_rewards_services),
) -> RewardItemResponse:
    view = await services.create_item.execute(admin, CreateItemCommand(**body.model_dump()))
    return RewardItemResponse.of(view)


@admin_router.patch(
    "/reward-items/{item_id}",
    response_model=RewardItemResponse,
    summary="Quản trị: sửa món đổi thưởng (F17.09)",
)
async def update_reward_item(
    item_id: int,
    body: UpdateRewardItemRequest,
    admin: Identity = Depends(require_admin),
    services: RewardsServices = Depends(get_rewards_services),
) -> RewardItemResponse:
    changes = body.model_dump(exclude_unset=True)
    return RewardItemResponse.of(await services.update_item.execute(admin, item_id, changes))


@admin_users_router.get(
    "/rewards",
    response_model=UserRewardsResponse,
    summary="Quản trị: ví, VIP, khung và lịch sử phần thưởng của người dùng (F17.10)",
)
async def get_user_rewards(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: RewardsServices = Depends(get_rewards_services),
) -> UserRewardsResponse:
    return UserRewardsResponse.of(await services.user_rewards.execute(admin, user_id, page, size), page, size)


@admin_users_router.post(
    "/vip-grants",
    response_model=WalletResponse,
    summary="Quản trị: cấp hoặc thu hồi VIP của người dùng (F17.10)",
)
async def grant_vip(
    body: VipGrantRequest,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: RewardsServices = Depends(get_rewards_services),
) -> WalletResponse:
    command = VipGrantCommand(
        user_id=user_id,
        reason=body.reason,
        days=body.days,
        revoke=body.revoke,
        request_id=body.request_id,
    )
    return WalletResponse.of(await services.grant_vip.execute(admin, command))


@admin_users_router.post(
    "/wallet-adjustments",
    response_model=WalletResponse,
    summary="Quản trị: điều chỉnh xu hoặc vé của người dùng (F17.10)",
)
async def adjust_wallet(
    body: WalletAdjustRequest,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: RewardsServices = Depends(get_rewards_services),
) -> WalletResponse:
    command = WalletAdjustCommand(user_id, Currency(body.currency), body.amount, body.reason, body.request_id)
    return WalletResponse.of(await services.adjust_wallet.execute(admin, command))


routers = [rewards_router, vip_router, admin_router, admin_users_router]
