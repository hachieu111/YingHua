from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rewards.domain.entities import ItemKind, NewRewardItem, Redemption, RewardItem
from app.modules.rewards.domain.errors import RewardItemCodeTakenError
from app.modules.rewards.infrastructure.orm_models import RewardItemModel, RewardRedemptionModel


def item_entity(m: RewardItemModel) -> RewardItem:
    return RewardItem(
        id=m.id,
        code=m.code,
        name=m.name,
        description=m.description,
        kind=ItemKind(m.kind),
        price_coins=m.price_coins,
        vip_days=m.vip_days,
        ticket_count=m.ticket_count,
        frame_id=m.frame_id,
        per_user_limit=m.per_user_limit,
        is_active=m.is_active,
        sort_order=m.sort_order,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def redemption_entity(m: RewardRedemptionModel) -> Redemption:
    return Redemption(m.id, m.user_id, m.item_id, m.price_coins, m.request_id, m.created_at)


class SqlShopRepository:
    """Danh mục đổi thưởng và lượt đổi (F17.07, F17.09)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_items(self, only_active: bool) -> list[RewardItem]:
        stmt = select(RewardItemModel).order_by(RewardItemModel.sort_order, RewardItemModel.id)
        if only_active:
            stmt = stmt.where(RewardItemModel.is_active.is_(True))
        return [item_entity(m) for m in await self._session.scalars(stmt)]

    async def get_item(self, item_id: int) -> RewardItem | None:
        model = await self._session.get(RewardItemModel, item_id)
        return item_entity(model) if model else None

    async def get_item_by_code(self, code: str) -> RewardItem | None:
        model = await self._session.scalar(select(RewardItemModel).where(RewardItemModel.code == code))
        return item_entity(model) if model else None

    async def add_item(self, item: NewRewardItem) -> RewardItem:
        model = RewardItemModel(
            code=item.code,
            name=item.name,
            description=item.description,
            kind=item.kind.value,
            price_coins=item.price_coins,
            vip_days=item.vip_days,
            ticket_count=item.ticket_count,
            frame_id=item.frame_id,
            per_user_limit=item.per_user_limit,
            is_active=item.is_active,
            sort_order=item.sort_order,
            updated_by=item.updated_by,
            created_at=item.created_at,
            updated_at=item.created_at,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:  # hai yêu cầu cùng tạo một mã món
            raise RewardItemCodeTakenError() from exc
        return item_entity(model)

    async def update_item(self, item: RewardItem, now: datetime) -> None:
        model = await self._session.get(RewardItemModel, item.id)
        if model is None:
            return
        model.name = item.name
        model.description = item.description
        model.price_coins = item.price_coins
        model.vip_days = item.vip_days
        model.ticket_count = item.ticket_count
        model.frame_id = item.frame_id
        model.per_user_limit = item.per_user_limit
        model.is_active = item.is_active
        model.sort_order = item.sort_order
        model.updated_by = item.updated_by
        model.updated_at = now
        await self._session.flush()

    async def count_redemptions_by_item(self, user_id: int) -> dict[int, int]:
        rows = await self._session.execute(
            select(RewardRedemptionModel.item_id, func.count())
            .where(RewardRedemptionModel.user_id == user_id)
            .group_by(RewardRedemptionModel.item_id)
        )
        return {item_id: int(n) for item_id, n in rows.all()}

    async def item_has_redemptions(self, item_id: int) -> bool:
        stmt = select(exists().where(RewardRedemptionModel.item_id == item_id))
        return bool(await self._session.scalar(stmt))

    async def get_redemption(self, user_id: int, request_id: uuid.UUID) -> Redemption | None:
        model = await self._session.scalar(
            select(RewardRedemptionModel).where(
                RewardRedemptionModel.user_id == user_id, RewardRedemptionModel.request_id == request_id
            )
        )
        return redemption_entity(model) if model else None

    async def add_redemption(
        self, user_id: int, item_id: int, price_coins: int, request_id: uuid.UUID, now: datetime
    ) -> Redemption:
        model = RewardRedemptionModel(
            user_id=user_id, item_id=item_id, price_coins=price_coins, request_id=request_id, created_at=now
        )
        self._session.add(model)
        await self._session.flush()
        return redemption_entity(model)
