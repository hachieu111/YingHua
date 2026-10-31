from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.domain.entities import (
    Season,
    SeasonResult,
    SeasonResultRow,
    SeasonStatus,
    SeasonTier,
)
from app.modules.gamification.infrastructure.orm_models import SeasonModel, SeasonResultModel, XpEventModel
from app.modules.gamification.infrastructure.vn_time_sql import vn_week_start

# Khóa tư vấn: một tiến trình tạo mùa tại một thời điểm, nên số kỳ tăng dần và không trùng.
_SEASON_CREATE_LOCK = 0x4D160001
_OPEN = (SeasonStatus.ACTIVE.value, SeasonStatus.FINALIZING.value)


def _season(m: SeasonModel) -> Season:
    return Season(m.id, m.number, m.starts_at, m.ends_at, SeasonStatus(m.status), m.finalized_at)


def _result(m: SeasonResultModel) -> SeasonResult:
    return SeasonResult(m.season_id, m.user_id, m.rank, m.xp, SeasonTier(m.tier), m.reward_granted_at)


class SqlSeasonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_containing(self, at: datetime) -> Season | None:
        row = await self._session.scalar(
            select(SeasonModel).where(SeasonModel.starts_at <= at, SeasonModel.ends_at > at)
        )
        return _season(row) if row else None

    async def ensure(self, starts_at: datetime, ends_at: datetime, now: datetime) -> tuple[Season, bool]:
        await self._session.execute(select(func.pg_advisory_xact_lock(_SEASON_CREATE_LOCK)))
        existing = await self._session.scalar(select(SeasonModel).where(SeasonModel.starts_at == starts_at))
        if existing is not None:
            return _season(existing), False
        next_number = select(func.coalesce(func.max(SeasonModel.number), 0) + 1).scalar_subquery()
        stmt = (
            pg_insert(SeasonModel)
            .values(number=next_number, starts_at=starts_at, ends_at=ends_at, created_at=now)
            .on_conflict_do_nothing(index_elements=[SeasonModel.starts_at])
            .returning(SeasonModel)
        )
        created = await self._session.scalar(stmt)
        if created is None:  # hai khóa tư vấn không thể cùng giữ; phòng khi ràng buộc duy nhất thắng
            row = await self._session.scalar(select(SeasonModel).where(SeasonModel.starts_at == starts_at))
            assert row is not None
            return _season(row), False
        return _season(created), True

    async def missing_week_starts(self, since: datetime, until: datetime) -> list[datetime]:
        week = vn_week_start(XpEventModel.created_at)
        rows = await self._session.scalars(
            select(week)
            .where(
                XpEventModel.created_at >= since,
                XpEventModel.created_at <= until,
                ~exists().where(SeasonModel.starts_at == week),
            )
            .distinct()
            .order_by(week)
        )
        return list(rows)

    async def has_unfinished_ended(self, now: datetime) -> bool:
        found = await self._session.scalar(
            select(SeasonModel.id)
            .where(SeasonModel.status != SeasonStatus.FINALIZED.value, SeasonModel.ends_at <= now)
            .limit(1)
        )
        return found is not None

    async def claim_ended(self, now: datetime, exclude_ids: Sequence[int]) -> Season | None:
        stmt = (
            select(SeasonModel)
            .where(SeasonModel.status.in_(_OPEN), SeasonModel.ends_at <= now)
            .order_by(SeasonModel.ends_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if exclude_ids:
            stmt = stmt.where(SeasonModel.id.not_in(list(exclude_ids)))
        row = await self._session.scalar(stmt)
        return _season(row) if row else None

    async def set_status(self, season_id: int, status: SeasonStatus, finalized_at: datetime | None) -> None:
        await self._session.execute(
            update(SeasonModel)
            .where(SeasonModel.id == season_id)
            .values(status=status.value, finalized_at=finalized_at)
        )

    async def add_results(self, results: Sequence[SeasonResult], now: datetime) -> None:
        if not results:
            return
        stmt = (
            pg_insert(SeasonResultModel)
            .values(
                [
                    {
                        "season_id": r.season_id,
                        "user_id": r.user_id,
                        "rank": r.rank,
                        "xp": r.xp,
                        "tier": r.tier.value,
                        "created_at": now,
                    }
                    for r in results
                ]
            )
            .on_conflict_do_nothing()
        )
        await self._session.execute(stmt)

    async def claim_pending_result(self, season_id: int, skip_users: Sequence[int]) -> SeasonResult | None:
        stmt = (
            select(SeasonResultModel)
            .where(SeasonResultModel.season_id == season_id, SeasonResultModel.reward_granted_at.is_(None))
            .order_by(SeasonResultModel.rank)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if skip_users:
            stmt = stmt.where(SeasonResultModel.user_id.not_in(list(skip_users)))
        row = await self._session.scalar(stmt)
        return _result(row) if row else None

    async def mark_granted(self, season_id: int, user_id: int, at: datetime) -> None:
        await self._session.execute(
            update(SeasonResultModel)
            .where(SeasonResultModel.season_id == season_id, SeasonResultModel.user_id == user_id)
            .values(reward_granted_at=at)
        )

    async def count_pending(self, season_id: int) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(SeasonResultModel)
            .where(SeasonResultModel.season_id == season_id, SeasonResultModel.reward_granted_at.is_(None))
        )
        return int(count or 0)

    async def results_of_user(
        self, user_id: int, offset: int, limit: int
    ) -> tuple[list[SeasonResultRow], int]:
        total = await self._session.scalar(
            select(func.count()).select_from(SeasonResultModel).where(SeasonResultModel.user_id == user_id)
        )
        rows = await self._session.execute(
            select(SeasonResultModel, SeasonModel)
            .join(SeasonModel, SeasonModel.id == SeasonResultModel.season_id)
            .where(SeasonResultModel.user_id == user_id)
            .order_by(SeasonModel.starts_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [SeasonResultRow(_result(r), _season(s)) for r, s in rows], int(total or 0)

    async def result_of_user(self, season_id: int, user_id: int) -> SeasonResult | None:
        row = await self._session.get(SeasonResultModel, (season_id, user_id))
        return _result(row) if row else None
