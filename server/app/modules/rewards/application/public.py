"""Bề mặt công khai của M17 cho module khác (M16, tác vụ nền). Module khác chỉ import từ đây.

- Ghi sổ phần thưởng idempotent (F17.01): `GrantRewardUseCase.execute(GrantCommand)` -> `GrantResult`.
  Ví dụ M16: khung mục tiêu tuần có hạn 7 ngày (F16.05)
  `GrantCommand(uid, RewardBundle(frame=FrameGrant("sakura_gold", FrameSource.WEEKLY_GOAL, days=7)), key)`;
  thưởng mùa (F16.10) khóa `season:<id>`; xu huy hiệu (F16.11) khóa `achievement:<mã>:<cấp>`.
- Đọc theo lô khung đang hiệu lực và dấu VIP (F17.08): `GetDecorationsUseCase.execute(user_ids)`.
"""

from __future__ import annotations

from app.modules.rewards.application.ai_policy import VipAwareAiPolicy, VipStatusReader, build_ai_policies
from app.modules.rewards.application.dto import GrantCommand, GrantResult, WalletSnapshot
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import Decoration, RewardNotifier, RewardsUnitOfWork
from app.modules.rewards.application.use_cases.get_decorations import GetDecorationsUseCase
from app.modules.rewards.application.use_cases.grant_reward import GrantRewardUseCase
from app.modules.rewards.application.use_cases.grant_welcome_gift import GrantWelcomeGiftUseCase
from app.modules.rewards.application.use_cases.remind_vip_expiry import RemindVipExpiryUseCase
from app.modules.rewards.domain.entities import (
    Currency,
    FrameGrant,
    FrameSource,
    LedgerReason,
    RewardBundle,
)

__all__ = [
    "Currency",
    "Decoration",
    "FrameGrant",
    "FrameSource",
    "GetDecorationsUseCase",
    "GrantCommand",
    "GrantResult",
    "GrantRewardUseCase",
    "GrantWelcomeGiftUseCase",
    "LedgerReason",
    "RemindVipExpiryUseCase",
    "RewardBundle",
    "RewardLedger",
    "RewardNotifier",
    "RewardsUnitOfWork",
    "VipAwareAiPolicy",
    "VipStatusReader",
    "WalletSnapshot",
    "build_ai_policies",
]
