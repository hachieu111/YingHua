from __future__ import annotations

import uuid
from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import GrantCommand, VipGrantCommand, WalletView
from app.modules.rewards.application.ledger import RewardLedger
from app.modules.rewards.application.ports import RewardNotifier, RewardsUnitOfWork
from app.modules.rewards.application.views import build_wallet_view
from app.modules.rewards.domain.entities import LedgerReason, RewardBundle
from app.modules.rewards.domain.errors import InvalidRewardError
from app.modules.rewards.domain.rules import MAX_VIP_DAYS_PER_GRANT, NOTE_MAX_LENGTH, clean_note


def admin_key(request_id: uuid.UUID) -> str:
    """Khóa sổ chống bấm đúp của thao tác quản trị (F17.10)."""
    return f"admin:{request_id}"


def require_reason(raw: str) -> str:
    reason = clean_note(raw)
    if reason is None:
        raise InvalidRewardError("Cần ghi lý do")
    if len(" ".join(raw.split())) > NOTE_MAX_LENGTH:
        raise InvalidRewardError(f"Lý do tối đa {NOTE_MAX_LENGTH} ký tự")
    return reason


class GrantVipUseCase:
    """F17.10 - Quản trị viên cấp hoặc thu hồi VIP của một người dùng (US-QT-18).

    Cấp: cộng dồn theo F17.03. Thu hồi: hạn VIP về hiện tại, ghi dòng sổ âm số ngày còn lại. Được phép tự
    cấp/thu cho chính mình (người dùng chốt 30/10/2026); mọi thao tác ghi nhật ký quản trị trong cùng giao
    dịch (`rewards.vip_granted`/`rewards.vip_revoked`), không ghi được thì hủy. Thông báo gửi sau khi lưu.
    """

    def __init__(
        self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock, notifier: RewardNotifier
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._notifier = notifier

    async def execute(self, actor: Identity, command: VipGrantCommand) -> WalletView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        reason = require_reason(command.reason)
        if command.revoke == (command.days is not None):
            raise InvalidRewardError("Chọn cấp số ngày VIP hoặc thu hồi VIP")
        now, target = self._clock.now(), command.user_id
        key = admin_key(command.request_id)
        async with self._uow_factory() as uow:
            ledger = RewardLedger(uow.wallets)
            if command.revoke:
                result = await ledger.revoke_vip(target, key, actor.user_id, reason, now)
                action = "rewards.vip_revoked"
                details = {"days": -result.entries[0].amount} if result.entries else {}
            else:
                days = command.days or 0
                if not 1 <= days <= MAX_VIP_DAYS_PER_GRANT:
                    raise InvalidRewardError(f"Số ngày VIP từ 1 đến {MAX_VIP_DAYS_PER_GRANT}")
                grant = GrantCommand(
                    target, RewardBundle(vip_days=days), key, LedgerReason.ADMIN_ADJUST, actor.user_id, reason
                )
                result = await ledger.apply(grant, now)
                action, details = "rewards.vip_granted", {"days": days}
            if result.duplicate:
                # Gửi lại cùng mã yêu cầu: trả ví hiện tại, không ghi nhật ký hay thông báo lần hai.
                return await build_wallet_view(uow.wallets, target, now)
            await uow.audit.add(
                actor.user_id,
                action,
                "user",
                target,
                {"target_user_id": target, "currency": "vip_days", **details, "reason": reason},
                now,
            )
            view = await build_wallet_view(uow.wallets, target, now)
            await uow.commit()
        if command.revoke:
            await self._notifier.vip_revoked(target, reason)
        elif result.wallet.vip_until is not None:
            await self._notifier.vip_granted(target, command.days or 0, result.wallet.vip_until, reason)
        return view
