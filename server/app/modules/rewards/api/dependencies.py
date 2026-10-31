from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.container import Container, get_container
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.use_cases.adjust_wallet import AdjustWalletUseCase
from app.modules.rewards.application.use_cases.create_reward_item import CreateRewardItemUseCase
from app.modules.rewards.application.use_cases.equip_frame import EquipFrameUseCase
from app.modules.rewards.application.use_cases.get_user_rewards import GetUserRewardsUseCase
from app.modules.rewards.application.use_cases.get_vip_overview import GetVipOverviewUseCase
from app.modules.rewards.application.use_cases.get_wallet import GetWalletUseCase
from app.modules.rewards.application.use_cases.grant_vip import GrantVipUseCase
from app.modules.rewards.application.use_cases.list_admin_frames import ListAdminFramesUseCase
from app.modules.rewards.application.use_cases.list_frames import ListFramesUseCase
from app.modules.rewards.application.use_cases.list_ledger import ListLedgerUseCase
from app.modules.rewards.application.use_cases.list_reward_items import ListRewardItemsUseCase
from app.modules.rewards.application.use_cases.list_shop_items import ListShopItemsUseCase
from app.modules.rewards.application.use_cases.list_unlocks import ListUnlocksUseCase
from app.modules.rewards.application.use_cases.redeem_item import RedeemItemUseCase
from app.modules.rewards.application.use_cases.set_series_vip import SetSeriesVipUseCase
from app.modules.rewards.application.use_cases.unlock_series import UnlockSeriesUseCase
from app.modules.rewards.application.use_cases.update_reward_item import UpdateRewardItemUseCase
from app.modules.rewards.infrastructure.notifier import build_reward_notifier
from app.modules.rewards.infrastructure.uow import SqlRewardsUnitOfWork


@dataclass(slots=True)
class RewardsServices:
    get_wallet: GetWalletUseCase
    list_ledger: ListLedgerUseCase
    vip_overview: GetVipOverviewUseCase
    unlock_series: UnlockSeriesUseCase
    list_unlocks: ListUnlocksUseCase
    list_shop: ListShopItemsUseCase
    redeem: RedeemItemUseCase
    list_frames: ListFramesUseCase
    equip_frame: EquipFrameUseCase
    set_series_vip: SetSeriesVipUseCase
    list_items: ListRewardItemsUseCase
    list_admin_frames: ListAdminFramesUseCase
    create_item: CreateRewardItemUseCase
    update_item: UpdateRewardItemUseCase
    user_rewards: GetUserRewardsUseCase
    grant_vip: GrantVipUseCase
    adjust_wallet: AdjustWalletUseCase


def build_rewards_services(container: Container) -> RewardsServices:
    def uow_factory() -> RewardsUnitOfWork:
        return SqlRewardsUnitOfWork(container.session_factory)

    clock = container.clock
    notifier = build_reward_notifier(
        container.session_factory, container.settings.storage_dir / "outbox", clock
    )
    return RewardsServices(
        get_wallet=GetWalletUseCase(uow_factory, clock),
        list_ledger=ListLedgerUseCase(uow_factory),
        vip_overview=GetVipOverviewUseCase(uow_factory, container.system_settings, clock),
        unlock_series=UnlockSeriesUseCase(uow_factory, clock),
        list_unlocks=ListUnlocksUseCase(uow_factory),
        list_shop=ListShopItemsUseCase(uow_factory),
        redeem=RedeemItemUseCase(uow_factory, clock),
        list_frames=ListFramesUseCase(uow_factory, clock),
        equip_frame=EquipFrameUseCase(uow_factory, clock),
        set_series_vip=SetSeriesVipUseCase(uow_factory, clock),
        list_items=ListRewardItemsUseCase(uow_factory),
        list_admin_frames=ListAdminFramesUseCase(uow_factory),
        create_item=CreateRewardItemUseCase(uow_factory, clock),
        update_item=UpdateRewardItemUseCase(uow_factory, clock),
        user_rewards=GetUserRewardsUseCase(uow_factory, clock),
        grant_vip=GrantVipUseCase(uow_factory, clock, notifier),
        adjust_wallet=AdjustWalletUseCase(uow_factory, clock, notifier),
    )


def get_rewards_services(container: Container = Depends(get_container)) -> RewardsServices:
    return build_rewards_services(container)
