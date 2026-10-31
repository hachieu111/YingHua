from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.application.dto import BadgeView
from app.modules.gamification.domain.entities import (
    Achievement,
    AchievementMetric,
    AchievementSource,
    UserAchievement,
)
from app.modules.gamification.infrastructure.orm_models import AchievementModel, UserAchievementModel


def _achievement(m: AchievementModel) -> Achievement:
    return Achievement(
        id=m.id,
        code=m.code,
        name=m.name,
        description=m.description,
        metric=AchievementMetric(m.metric),
        thresholds=tuple(m.thresholds),
        coin_rewards=tuple(m.coin_rewards),
        style_key=m.style_key,
        sort_order=m.sort_order,
    )


def _user_achievement(m: UserAchievementModel) -> UserAchievement:
    return UserAchievement(
        m.user_id,
        m.achievement_id,
        m.tier,
        AchievementSource(m.source),
        m.is_equipped,
        m.unlocked_at,
        m.tier_reached_at,
    )


class SqlAchievementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[Achievement]:
        rows = await self._session.scalars(
            select(AchievementModel)
            .where(AchievementModel.is_active.is_(True))
            .order_by(AchievementModel.sort_order, AchievementModel.id)
        )
        return [_achievement(r) for r in rows]

    async def get_by_code(self, code: str) -> Achievement | None:
        row = await self._session.scalar(
            select(AchievementModel).where(
                AchievementModel.code == code, AchievementModel.is_active.is_(True)
            )
        )
        return _achievement(row) if row else None

    async def user_rows(self, user_id: int) -> dict[int, UserAchievement]:
        rows = await self._session.scalars(
            select(UserAchievementModel).where(UserAchievementModel.user_id == user_id)
        )
        return {r.achievement_id: _user_achievement(r) for r in rows}

    async def upsert_tier(
        self, user_id: int, achievement_id: int, tier: int, source: AchievementSource, now: datetime
    ) -> None:
        stmt = pg_insert(UserAchievementModel).values(
            user_id=user_id,
            achievement_id=achievement_id,
            tier=tier,
            source=source.value,
            unlocked_at=now,
            tier_reached_at=now,
        )
        # Chỉ nâng cấp, không bao giờ hạ (hai lần đánh giá đồng thời); giữ nguồn và ngày mở khóa đầu tiên.
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserAchievementModel.user_id, UserAchievementModel.achievement_id],
            set_={"tier": stmt.excluded.tier, "tier_reached_at": now},
            where=UserAchievementModel.tier < stmt.excluded.tier,
        )
        await self._session.execute(stmt)

    async def equipped_for(self, user_ids: Sequence[int]) -> dict[int, BadgeView]:
        if not user_ids:
            return {}
        rows = await self._session.execute(
            select(
                UserAchievementModel.user_id,
                AchievementModel.code,
                AchievementModel.name,
                UserAchievementModel.tier,
                AchievementModel.style_key,
            )
            .join(AchievementModel, AchievementModel.id == UserAchievementModel.achievement_id)
            .where(
                UserAchievementModel.user_id.in_(list(user_ids)), UserAchievementModel.is_equipped.is_(True)
            )
        )
        return {uid: BadgeView(code, name, tier, style) for uid, code, name, tier, style in rows}

    async def set_equipped(self, user_id: int, achievement_id: int | None) -> None:
        await self._session.execute(
            update(UserAchievementModel)
            .where(UserAchievementModel.user_id == user_id, UserAchievementModel.is_equipped.is_(True))
            .values(is_equipped=False)
        )
        if achievement_id is None:
            return
        await self._session.execute(
            update(UserAchievementModel)
            .where(
                UserAchievementModel.user_id == user_id, UserAchievementModel.achievement_id == achievement_id
            )
            .values(is_equipped=True)
        )
