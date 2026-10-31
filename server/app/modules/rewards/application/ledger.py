"""Ghi sổ phần thưởng (F17.01): cổng duy nhất làm đổi số xu, số vé, hạn VIP và khung sở hữu.

Luôn chạy trong giao dịch của bên gọi: khóa dòng ví trước, kiểm khóa chống trùng và số dư rồi mới ghi, nên hai
yêu cầu đồng thời của cùng một người không thể cùng tiêu một số dư.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from app.modules.rewards.application.dto import GrantCommand, GrantResult, WalletSnapshot
from app.modules.rewards.application.ports import WalletRepository
from app.modules.rewards.domain.entities import (
    Currency,
    FrameGrant,
    LedgerEntry,
    LedgerReason,
    NewLedgerEntry,
    UserFrame,
    Wallet,
)
from app.modules.rewards.domain.errors import (
    InvalidRewardError,
    NotEnoughCoinsError,
    NotEnoughTicketsError,
    TicketLimitReachedError,
    VipNotActiveError,
)
from app.modules.rewards.domain.rules import (
    MAX_TICKET_BALANCE,
    STRICT_TICKET_REASONS,
    clean_note,
    extend_vip,
    validate_bundle,
    vip_days_left,
)


def snapshot_of(wallet: Wallet) -> WalletSnapshot:
    return WalletSnapshot(
        wallet.user_id,
        wallet.coin_balance,
        wallet.ticket_balance,
        wallet.vip_until,
        wallet.equipped_frame_id,
    )


class RewardLedger:
    def __init__(self, wallets: WalletRepository) -> None:
        self._wallets = wallets

    async def apply(self, cmd: GrantCommand, now: datetime) -> GrantResult:
        """Trao gói thưởng/khoản trừ. Lỗi (không đủ số dư...) thì không ghi gì, bên gọi không commit."""
        bundle = cmd.bundle
        validate_bundle(bundle)
        if bundle.has_currency and cmd.reason is None:
            raise InvalidRewardError("Thiếu lý do ghi sổ phần thưởng")
        wallet = await self._wallets.lock_wallet(cmd.user_id, now)
        steps: list[Callable[[Wallet, GrantCommand, datetime], Awaitable[LedgerEntry | None]]] = []
        if bundle.coins:
            steps.append(self._apply_coins)
        if bundle.tickets:
            steps.append(self._apply_tickets)
        if bundle.vip_days:
            steps.append(self._apply_vip_days)
        entries = [e for e in [await step(wallet, cmd, now) for step in steps] if e is not None]
        # Mọi loại đã được ghi trước đó (cùng khóa): gọi lại không làm gì, kể cả khung đi kèm.
        duplicate = bool(steps) and not entries
        frame: UserFrame | None = None
        if bundle.frame is not None and not duplicate:
            frame = await self._grant_frame(cmd.user_id, bundle.frame, now)
        if entries:
            await self._wallets.save_wallet(wallet, now)
        return GrantResult(snapshot_of(wallet), entries, duplicate, frame)

    async def revoke_vip(
        self, user_id: int, key: str, actor_id: int, note: str | None, now: datetime
    ) -> GrantResult:
        """Thu hồi VIP (F17.10): hạn về hiện tại, ghi dòng sổ âm số ngày còn lại (làm tròn lên, ≥ 1)."""
        wallet = await self._wallets.lock_wallet(user_id, now)
        if await self._wallets.has_ledger_key(user_id, Currency.VIP_DAYS, key):
            return GrantResult(snapshot_of(wallet), [], duplicate=True)
        if not wallet.is_vip(now) or wallet.vip_until is None:
            raise VipNotActiveError()
        removed = vip_days_left(wallet.vip_until, now)
        wallet.vip_until = now
        entry = await self._wallets.add_ledger(
            NewLedgerEntry(
                user_id=user_id,
                currency=Currency.VIP_DAYS,
                amount=-removed,
                reason=LedgerReason.ADMIN_ADJUST,
                idempotency_key=key,
                created_at=now,
                vip_until_after=now,
                note=clean_note(note),
                actor_id=actor_id,
            )
        )
        await self._wallets.save_wallet(wallet, now)
        return GrantResult(snapshot_of(wallet), [entry])

    async def _apply_coins(self, wallet: Wallet, cmd: GrantCommand, now: datetime) -> LedgerEntry | None:
        amount = cmd.bundle.coins
        if await self._wallets.has_ledger_key(wallet.user_id, Currency.COIN, cmd.key):
            return None
        new_balance = wallet.coin_balance + amount
        if new_balance < 0:
            raise NotEnoughCoinsError(
                details={
                    "required": -amount,
                    "balance": wallet.coin_balance,
                    "missing": -new_balance,
                }
            )
        wallet.coin_balance = new_balance
        return await self._record(wallet, cmd, Currency.COIN, amount, now, balance_after=new_balance)

    async def _apply_tickets(self, wallet: Wallet, cmd: GrantCommand, now: datetime) -> LedgerEntry | None:
        amount = cmd.bundle.tickets
        if await self._wallets.has_ledger_key(wallet.user_id, Currency.TICKET, cmd.key):
            return None
        new_balance = wallet.ticket_balance + amount
        if new_balance < 0:
            raise NotEnoughTicketsError(
                details={"required": -amount, "balance": wallet.ticket_balance, "missing": -new_balance}
            )
        if new_balance > MAX_TICKET_BALANCE:
            if cmd.reason in STRICT_TICKET_REASONS:
                raise TicketLimitReachedError(details={"limit": MAX_TICKET_BALANCE})
            # Thưởng tự động (mùa, mốc chuỗi...) không được kẹt vì ví đầy: cắt về trần, phần thừa mất.
            amount = MAX_TICKET_BALANCE - wallet.ticket_balance
            new_balance = MAX_TICKET_BALANCE
            if amount <= 0:
                return None
        wallet.ticket_balance = new_balance
        return await self._record(wallet, cmd, Currency.TICKET, amount, now, balance_after=new_balance)

    async def _apply_vip_days(self, wallet: Wallet, cmd: GrantCommand, now: datetime) -> LedgerEntry | None:
        days = cmd.bundle.vip_days
        if await self._wallets.has_ledger_key(wallet.user_id, Currency.VIP_DAYS, cmd.key):
            return None
        wallet.vip_until = extend_vip(wallet.vip_until, days, now)
        return await self._record(wallet, cmd, Currency.VIP_DAYS, days, now, vip_until_after=wallet.vip_until)

    async def _record(
        self,
        wallet: Wallet,
        cmd: GrantCommand,
        currency: Currency,
        amount: int,
        now: datetime,
        *,
        balance_after: int | None = None,
        vip_until_after: datetime | None = None,
    ) -> LedgerEntry:
        assert cmd.reason is not None  # đã kiểm ở apply()
        return await self._wallets.add_ledger(
            NewLedgerEntry(
                user_id=wallet.user_id,
                currency=currency,
                amount=amount,
                reason=cmd.reason,
                idempotency_key=cmd.key,
                created_at=now,
                balance_after=balance_after,
                vip_until_after=vip_until_after,
                note=clean_note(cmd.note),
                actor_id=cmd.actor_id,
            )
        )

    async def _grant_frame(self, user_id: int, grant: FrameGrant, now: datetime) -> UserFrame:
        """Khung vĩnh viễn thắng khung có hạn; khung có hạn nhận lại thì gia hạn tới mốc muộn hơn (F17.08)."""
        frame = await self._wallets.get_frame_by_code(grant.code)
        if frame is None or not frame.is_active:
            raise InvalidRewardError("Khung avatar không tồn tại")
        expires = None if grant.days is None else now + timedelta(days=grant.days)
        current = await self._wallets.get_user_frame(user_id, frame.id)
        if current is None:
            saved = UserFrame(user_id, frame.id, grant.source, now, expires)
        elif current.is_permanent:
            return current
        else:
            if expires is not None and current.expires_at is not None:
                expires = max(expires, current.expires_at)
            source = grant.source if expires is None else current.source
            saved = UserFrame(user_id, frame.id, source, current.acquired_at, expires)
        await self._wallets.save_user_frame(saved)
        return saved
