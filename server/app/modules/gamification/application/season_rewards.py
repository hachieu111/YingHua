"""Phần thưởng của ba bậc mùa thi đua (F16.09). Hằng số của M16; M17 chỉ ghi sổ."""

from __future__ import annotations

from app.modules.gamification.application.dto import TierInfo
from app.modules.gamification.domain.achievement_rules import SEASON_TOP3_CODE, SEASON_TOP50_CODE
from app.modules.gamification.domain.entities import SeasonTier
from app.modules.rewards.application.public import FrameGrant, FrameSource, RewardBundle

TIER_RANKS: dict[SeasonTier, tuple[int, int]] = {
    SeasonTier.TOP3: (1, 3),
    SeasonTier.TOP10: (4, 10),
    SeasonTier.TOP50: (11, 50),
}
SEASON_REWARDS: dict[SeasonTier, RewardBundle] = {
    SeasonTier.TOP3: RewardBundle(vip_days=30, frame=FrameGrant("sakura_gold", FrameSource.SEASON)),
    SeasonTier.TOP10: RewardBundle(tickets=3, frame=FrameGrant("spring_petal", FrameSource.SEASON)),
    SeasonTier.TOP50: RewardBundle(coins=500),
}
# Huy hiệu mùa trao kèm (top 11-50 chỉ trao cấp I nếu chưa có). Bậc top 4-10 không có huy hiệu.
SEASON_BADGES: dict[SeasonTier, str] = {
    SeasonTier.TOP3: SEASON_TOP3_CODE,
    SeasonTier.TOP50: SEASON_TOP50_CODE,
}


def season_key(season_id: int) -> str:
    return f"season:{season_id}"


def tier_infos() -> list[TierInfo]:
    out: list[TierInfo] = []
    for tier, (low, high) in TIER_RANKS.items():
        bundle = SEASON_REWARDS[tier]
        out.append(
            TierInfo(
                tier,
                low,
                high,
                coins=bundle.coins,
                tickets=bundle.tickets,
                vip_days=bundle.vip_days,
                frame_code=bundle.frame.code if bundle.frame else None,
                badge_code=SEASON_BADGES.get(tier),
            )
        )
    return out
