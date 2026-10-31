"""Chỉ số huy hiệu, tính khi đánh giá từ dữ liệu của module khác (docs/database-design.md §4.18)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Select, distinct, exists, extract, func, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.domain.achievement_rules import (
    HSK3_LEVEL,
    HSK3_MASTERED_STABILITY_DAYS,
    NIGHT_END_HOUR,
    NIGHT_START_HOUR,
)
from app.modules.gamification.domain.entities import AchievementMetric
from app.modules.gamification.infrastructure.foreign_tables import cards
from app.modules.gamification.infrastructure.foreign_tables import daily_activities as da
from app.modules.gamification.infrastructure.foreign_tables import lookup_events as le
from app.modules.gamification.infrastructure.foreign_tables import page_reads as pr
from app.modules.gamification.infrastructure.foreign_tables import vocab_entries as ve

_LOOKUP_ACTIONS = ("hover", "lookup")
_KNOWN_STATUS = "known"
_REVIEW_STATE = "review"


class SqlMetricReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def values(
        self, user_id: int, metrics: Iterable[AchievementMetric], timezone: str
    ) -> dict[AchievementMetric, int]:
        out: dict[AchievementMetric, int] = {}
        for metric in dict.fromkeys(metrics):
            query = self._query(metric, user_id, timezone)
            if query is not None:
                out[metric] = int(await self._session.scalar(query) or 0)
        return out

    @staticmethod
    def _query(metric: AchievementMetric, user_id: int, timezone: str) -> Select[tuple[int]] | None:
        match metric:
            case AchievementMetric.STUDY_DAYS:
                return (
                    select(func.count())
                    .select_from(da)
                    .where(da.c.user_id == user_id, da.c.reviews_count + da.c.pages_read > 0)
                )
            case AchievementMetric.PAGES_READ:
                return select(func.count()).select_from(pr).where(pr.c.user_id == user_id)
            case AchievementMetric.WORDS_SAVED:
                return select(func.count()).select_from(ve).where(ve.c.user_id == user_id)
            case AchievementMetric.HSK3_MASTERED:
                has_stable_card = exists().where(
                    cards.c.vocab_entry_id == ve.c.id,
                    cards.c.state == _REVIEW_STATE,
                    cards.c.stability >= HSK3_MASTERED_STABILITY_DAYS,
                )
                return (
                    select(func.count())
                    .select_from(ve)
                    .where(
                        ve.c.user_id == user_id,
                        ve.c.hsk_level == HSK3_LEVEL,
                        or_(ve.c.status == _KNOWN_STATUS, has_stable_card),
                    )
                )
            case AchievementMetric.NIGHT_PAGES:
                hour = extract("hour", func.timezone(timezone, pr.c.first_read_at))
                return (
                    select(func.count())
                    .select_from(pr)
                    .where(pr.c.user_id == user_id, or_(hour >= NIGHT_START_HOUR, hour < NIGHT_END_HOUR))
                )
            case AchievementMetric.BUBBLE_LOOKUPS:
                return (
                    select(func.count(distinct(le.c.bubble_id)))
                    .select_from(le)
                    .where(
                        le.c.user_id == user_id,
                        le.c.action.in_(_LOOKUP_ACTIONS),
                        le.c.bubble_id.is_not(None),
                    )
                )
            case AchievementMetric.SEASON_TOP3:
                return None
        return None

    async def active_users(self, since: datetime, after_user_id: int, limit: int) -> list[int]:
        learned = select(da.c.user_id.label("user_id")).where(da.c.updated_at >= since)
        looked_up = select(le.c.user_id.label("user_id")).where(le.c.created_at >= since)
        active = union(learned, looked_up).subquery()
        rows = await self._session.scalars(
            select(active.c.user_id)
            .where(active.c.user_id > after_user_id)
            .order_by(active.c.user_id)
            .limit(limit)
        )
        return [int(r) for r in rows]
