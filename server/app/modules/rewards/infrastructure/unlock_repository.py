from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rewards.domain.entities import UnlockSource, VipUnlock
from app.modules.rewards.infrastructure.orm_models import VipUnlockModel


def _entity(m: VipUnlockModel) -> VipUnlock:
    return VipUnlock(m.user_id, m.series_id, UnlockSource(m.source), m.unlocked_at)


class SqlUnlockRepository:
    """Truyện VIP đã mở khóa bằng vé (F17.06)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int, series_id: int) -> VipUnlock | None:
        model = await self._session.get(VipUnlockModel, (user_id, series_id))
        return _entity(model) if model else None

    async def add(self, unlock: VipUnlock) -> None:
        self._session.add(
            VipUnlockModel(
                user_id=unlock.user_id,
                series_id=unlock.series_id,
                source=unlock.source.value,
                unlocked_at=unlock.unlocked_at,
            )
        )
        await self._session.flush()

    async def list_for_user(self, user_id: int) -> list[VipUnlock]:
        rows = await self._session.scalars(
            select(VipUnlockModel)
            .where(VipUnlockModel.user_id == user_id)
            .order_by(VipUnlockModel.unlocked_at.desc(), VipUnlockModel.series_id.desc())
        )
        return [_entity(m) for m in rows]
