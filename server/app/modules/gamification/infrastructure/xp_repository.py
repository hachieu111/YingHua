from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.domain.entities import NewXpEvent, XpSource
from app.modules.gamification.domain.xp_rules import ACTIVITY_SOURCES
from app.modules.gamification.infrastructure.orm_models import XpEventModel as Row
from app.modules.gamification.infrastructure.vn_time_sql import vn_date_of

# Khóa tư vấn (advisory lock) của sổ XP: [tiền tố 32 bit | mã người dùng 32 bit] để khóa theo từng người.
_XP_LOCK_PREFIX = 0x4D16


class SqlXpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_user(self, user_id: int) -> None:
        key = (_XP_LOCK_PREFIX << 32) | (user_id & 0xFFFFFFFF)
        await self._session.execute(select(func.pg_advisory_xact_lock(key)))

    async def exists(self, user_id: int, source: XpSource, source_ref: str) -> bool:
        found = await self._session.scalar(
            select(Row.id).where(
                Row.user_id == user_id, Row.source == source.value, Row.source_ref == source_ref
            )
        )
        return found is not None

    async def insert_if_absent(self, event: NewXpEvent) -> bool:
        stmt = (
            pg_insert(Row)
            .values(
                user_id=event.user_id,
                source=event.source.value,
                source_ref=event.source_ref,
                amount=event.amount,
                capped=event.capped,
                activity_date=event.activity_date,
                created_at=event.created_at,
            )
            .on_conflict_do_nothing(index_elements=[Row.user_id, Row.source, Row.source_ref])
            .returning(Row.id)
        )
        return (await self._session.scalar(stmt)) is not None

    async def count_for_day(self, user_id: int, day: date, source: XpSource) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(Row)
            .where(Row.user_id == user_id, Row.activity_date == day, Row.source == source.value)
        )
        return int(count or 0)

    async def activity_xp_for_day(self, user_id: int, day: date) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(Row.amount), 0)).where(
                Row.user_id == user_id,
                Row.activity_date == day,
                Row.source.in_([s.value for s in ACTIVITY_SOURCES]),
            )
        )
        return int(total or 0)

    async def rewarded_at(self, user_id: int, source: XpSource, refs: Sequence[str]) -> dict[str, datetime]:
        rows = await self._session.execute(
            select(Row.source_ref, Row.created_at).where(
                Row.user_id == user_id, Row.source == source.value, Row.source_ref.in_(list(refs))
            )
        )
        return {ref: at for ref, at in rows}

    async def xp_for_day(self, user_id: int, day: date) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(Row.amount), 0)).where(
                Row.user_id == user_id, Row.activity_date == day
            )
        )
        return int(total or 0)

    async def xp_between(self, user_id: int, start_at: datetime, end_at: datetime) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(Row.amount), 0)).where(
                Row.user_id == user_id, Row.created_at >= start_at, Row.created_at < end_at
            )
        )
        return int(total or 0)

    async def xp_total(self, user_id: int) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(Row.amount), 0)).where(Row.user_id == user_id)
        )
        return int(total or 0)

    async def xp_by_vn_day(self, user_id: int, start_at: datetime, end_at: datetime) -> dict[date, int]:
        day = vn_date_of(Row.created_at)
        rows = await self._session.execute(
            select(day, func.sum(Row.amount))
            .where(Row.user_id == user_id, Row.created_at >= start_at, Row.created_at < end_at)
            .group_by(day)
        )
        return {d: int(total) for d, total in rows}
