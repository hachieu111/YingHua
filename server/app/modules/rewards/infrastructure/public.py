"""Hiện thực M17 mà tầng lắp ghép (container, worker) và hạ tầng của module khác được dùng."""

from __future__ import annotations

from app.modules.rewards.infrastructure.notifier import NotificationsRewardNotifier, build_reward_notifier
from app.modules.rewards.infrastructure.uow import SqlRewardsUnitOfWork
from app.modules.rewards.infrastructure.vip_access import SqlVipAccess, SqlVipStatusReader
from app.modules.rewards.infrastructure.wallet_repository import SqlWalletRepository

__all__ = [
    "NotificationsRewardNotifier",
    "SqlRewardsUnitOfWork",
    "SqlVipAccess",
    "SqlVipStatusReader",
    "SqlWalletRepository",
    "build_reward_notifier",
]
