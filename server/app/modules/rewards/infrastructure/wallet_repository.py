from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rewards.application.ports import Decoration, ExpiringVip
from app.modules.rewards.domain.entities import (
    AvatarFrame,
    Currency,
    FrameAcquireKind,
    FrameSource,
    LedgerEntry,
    LedgerReason,
    NewLedgerEntry,
    UserFrame,
    Wallet,
)
from app.modules.rewards.infrastructure.foreign_tables import users
from app.modules.rewards.infrastructure.orm_models import (
    AvatarFrameModel,
    UserFrameModel,
    WalletLedgerModel,
    WalletModel,
)


def wallet_entity(m: WalletModel) -> Wallet:
    return Wallet(
        user_id=m.user_id,
        coin_balance=m.coin_balance,
        ticket_balance=m.ticket_balance,
        vip_until=m.vip_until,
        vip_reminded_for=m.vip_reminded_for,
        equipped_frame_id=m.equipped_frame_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def frame_entity(m: AvatarFrameModel) -> AvatarFrame:
    return AvatarFrame(
        id=m.id,
        code=m.code,
        name=m.name,
        description=m.description,
        style_key=m.style_key,
        acquire_kind=FrameAcquireKind(m.acquire_kind),
        is_active=m.is_active,
    )


def user_frame_entity(m: UserFrameModel) -> UserFrame:
    return UserFrame(m.user_id, m.frame_id, FrameSource(m.source), m.acquired_at, m.expires_at)


def ledger_entity(m: WalletLedgerModel) -> LedgerEntry:
    return LedgerEntry(
        id=m.id,
        user_id=m.user_id,
        currency=Currency(m.currency),
        amount=m.amount,
        reason=LedgerReason(m.reason),
        idempotency_key=m.idempotency_key,
        created_at=m.created_at,
        balance_after=m.balance_after,
        vip_until_after=m.vip_until_after,
        note=m.note,
        actor_id=m.actor_id,
    )


class SqlWalletRepository:
    """Ví, sổ phần thưởng và khung avatar. `lock_wallet` giữ khóa dòng ví tới hết giao dịch (F17.01)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_wallet(self, user_id: int, now: datetime) -> Wallet:
        await self._session.execute(
            pg_insert(WalletModel)
            .values(user_id=user_id, created_at=now, updated_at=now)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        model = (
            await self._session.execute(
                select(WalletModel)
                .where(WalletModel.user_id == user_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return wallet_entity(model)

    async def get_wallet(self, user_id: int) -> Wallet | None:
        model = await self._session.get(WalletModel, user_id)
        return wallet_entity(model) if model else None

    async def save_wallet(self, wallet: Wallet, now: datetime) -> None:
        await self._session.execute(
            update(WalletModel)
            .where(WalletModel.user_id == wallet.user_id)
            .values(
                coin_balance=wallet.coin_balance,
                ticket_balance=wallet.ticket_balance,
                vip_until=wallet.vip_until,
                equipped_frame_id=wallet.equipped_frame_id,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )

    async def has_ledger_key(self, user_id: int, currency: Currency, key: str) -> bool:
        stmt = select(
            exists().where(
                WalletLedgerModel.user_id == user_id,
                WalletLedgerModel.currency == currency.value,
                WalletLedgerModel.idempotency_key == key,
            )
        )
        return bool(await self._session.scalar(stmt))

    async def add_ledger(self, entry: NewLedgerEntry) -> LedgerEntry:
        model = WalletLedgerModel(
            user_id=entry.user_id,
            currency=entry.currency.value,
            amount=entry.amount,
            balance_after=entry.balance_after,
            vip_until_after=entry.vip_until_after,
            reason=entry.reason.value,
            idempotency_key=entry.idempotency_key,
            note=entry.note,
            actor_id=entry.actor_id,
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return ledger_entity(model)

    async def list_ledger(
        self, user_id: int, currency: Currency | None, offset: int, limit: int
    ) -> tuple[list[LedgerEntry], int]:
        conds = [WalletLedgerModel.user_id == user_id]
        if currency is not None:
            conds.append(WalletLedgerModel.currency == currency.value)
        total = await self._session.scalar(select(func.count()).select_from(WalletLedgerModel).where(*conds))
        rows = await self._session.scalars(
            select(WalletLedgerModel)
            .where(*conds)
            .order_by(WalletLedgerModel.created_at.desc(), WalletLedgerModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [ledger_entity(m) for m in rows], int(total or 0)

    async def get_frame_by_code(self, code: str) -> AvatarFrame | None:
        model = await self._session.scalar(select(AvatarFrameModel).where(AvatarFrameModel.code == code))
        return frame_entity(model) if model else None

    async def get_frame(self, frame_id: int) -> AvatarFrame | None:
        model = await self._session.get(AvatarFrameModel, frame_id)
        return frame_entity(model) if model else None

    async def list_frames(self) -> list[AvatarFrame]:
        rows = await self._session.scalars(
            select(AvatarFrameModel).where(AvatarFrameModel.is_active.is_(True)).order_by(AvatarFrameModel.id)
        )
        return [frame_entity(m) for m in rows]

    async def get_user_frame(self, user_id: int, frame_id: int) -> UserFrame | None:
        model = await self._session.get(UserFrameModel, (user_id, frame_id))
        return user_frame_entity(model) if model else None

    async def list_user_frames(self, user_id: int) -> list[UserFrame]:
        rows = await self._session.scalars(select(UserFrameModel).where(UserFrameModel.user_id == user_id))
        return [user_frame_entity(m) for m in rows]

    async def save_user_frame(self, frame: UserFrame) -> None:
        stmt = pg_insert(UserFrameModel).values(
            user_id=frame.user_id,
            frame_id=frame.frame_id,
            source=frame.source.value,
            acquired_at=frame.acquired_at,
            expires_at=frame.expires_at,
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id", "frame_id"],
                set_={"source": stmt.excluded.source, "expires_at": stmt.excluded.expires_at},
            )
        )

    async def decorations(self, user_ids: Sequence[int], now: datetime) -> dict[int, Decoration]:
        """Một truy vấn cho cả lô: ví nối khung đang đeo và bản ghi sở hữu của chính khung đó."""
        if not user_ids:
            return {}
        stmt = (
            select(
                WalletModel.user_id,
                WalletModel.vip_until,
                AvatarFrameModel,
                UserFrameModel.frame_id,
                UserFrameModel.expires_at,
            )
            .select_from(WalletModel)
            .outerjoin(AvatarFrameModel, AvatarFrameModel.id == WalletModel.equipped_frame_id)
            .outerjoin(
                UserFrameModel,
                and_(
                    UserFrameModel.user_id == WalletModel.user_id,
                    UserFrameModel.frame_id == WalletModel.equipped_frame_id,
                ),
            )
            .where(WalletModel.user_id.in_(list(user_ids)))
        )
        result: dict[int, Decoration] = {}
        for user_id, vip_until, frame_model, owned_id, owned_expires in (
            await self._session.execute(stmt)
        ).all():
            is_vip = vip_until is not None and vip_until > now
            frame = None
            if frame_model is not None and frame_model.is_active:
                if frame_model.acquire_kind == FrameAcquireKind.VIP.value:
                    usable = is_vip
                else:
                    usable = owned_id is not None and (owned_expires is None or owned_expires > now)
                frame = frame_entity(frame_model) if usable else None
            result[user_id] = Decoration(is_vip, frame)
        return result

    async def list_expiring_vip(
        self, now: datetime, until: datetime, after_user_id: int, limit: int
    ) -> list[ExpiringVip]:
        stmt = (
            select(WalletModel.user_id, WalletModel.vip_until)
            .join(users, users.c.id == WalletModel.user_id)
            .where(
                WalletModel.user_id > after_user_id,
                WalletModel.vip_until > now,
                WalletModel.vip_until <= until,
                WalletModel.vip_reminded_for.is_distinct_from(WalletModel.vip_until),
                users.c.status == "active",
            )
            .order_by(WalletModel.user_id)
            .limit(limit)
        )
        return [ExpiringVip(uid, vip_until) for uid, vip_until in (await self._session.execute(stmt)).all()]

    async def mark_vip_reminded(self, user_id: int, vip_until: datetime) -> bool:
        result = await self._session.execute(
            update(WalletModel)
            .where(WalletModel.user_id == user_id, WalletModel.vip_until == vip_until)
            .values(vip_reminded_for=vip_until)
        )
        return bool(getattr(result, "rowcount", 0))
