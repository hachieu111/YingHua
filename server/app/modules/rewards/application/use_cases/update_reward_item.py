from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import AdminItemView
from app.modules.rewards.application.item_rules import resolve_shop_frame
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.use_cases.create_reward_item import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
)
from app.modules.rewards.domain.entities import AvatarFrame, ItemKind, RewardItem
from app.modules.rewards.domain.errors import (
    InvalidRewardError,
    RewardItemLockedError,
    RewardItemNotFoundError,
)
from app.modules.rewards.domain.rules import clean_note, validate_item_kind_fields, validate_price

_PLAIN_FIELDS = frozenset({"name", "description", "price_coins", "per_user_limit", "is_active", "sort_order"})
_TARGET_FIELDS = frozenset({"vip_days", "ticket_count", "frame_code"})  # đối tượng của món
ALLOWED_FIELDS = _PLAIN_FIELDS | _TARGET_FIELDS
# Chỉ mô tả và giới hạn mỗi người được xóa bằng null tường minh; trường không gửi thì giữ nguyên.
_NOT_NULLABLE_FIELDS = frozenset({"name", "price_coins", "is_active", "sort_order"})


class UpdateRewardItemUseCase:
    """F17.09 - Sửa tên, mô tả, giá, giới hạn, trạng thái bán, thứ tự của món (US-QT-17).

    Không đổi loại món. Món đã có lượt đổi không đổi được đối tượng (số ngày VIP, số vé, khung), chỉ ngừng bán
    được, để lịch sử đổi giữ nguyên nghĩa. Ghi nhật ký `reward_item.updated` kèm các trường đã đổi.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, actor: Identity, item_id: int, changes: dict[str, Any]) -> AdminItemView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        if unknown := set(changes) - ALLOWED_FIELDS:
            raise InvalidRewardError(f"Trường không được sửa: {', '.join(sorted(unknown))}")
        if null_fields := {k for k in changes if k in _NOT_NULLABLE_FIELDS and changes[k] is None}:
            raise InvalidRewardError(f"Trường không được để trống: {', '.join(sorted(null_fields))}")
        now = self._clock.now()
        async with self._uow_factory() as uow:
            item = await uow.shop.get_item(item_id)
            if item is None:
                raise RewardItemNotFoundError()
            locked = await uow.shop.item_has_redemptions(item_id)
            frame = await uow.wallets.get_frame(item.frame_id) if item.frame_id is not None else None
            diff: dict[str, dict[str, Any]] = {}
            for key, value in changes.items():
                if key in _TARGET_FIELDS:
                    frame = await self._apply_target(uow, item, key, value, locked, frame, diff)
                else:
                    self._apply_plain(item, key, value, diff)
            validate_item_kind_fields(item.kind, item.vip_days, item.ticket_count, item.frame_id)
            if diff:
                item.updated_by = actor.user_id
                await uow.shop.update_item(item, now)
                await uow.audit.add(
                    actor.user_id,
                    "reward_item.updated",
                    "reward_item",
                    item_id,
                    {"code": item.code, "changes": diff},
                    now,
                )
            await uow.commit()
        return AdminItemView(item, frame, locked)

    @staticmethod
    def _apply_plain(item: RewardItem, key: str, value: Any, diff: dict[str, dict[str, Any]]) -> None:
        if key == "name":
            value = " ".join(str(value or "").split())
            if not value or len(value) > NAME_MAX_LENGTH:
                raise InvalidRewardError(f"Tên món từ 1 đến {NAME_MAX_LENGTH} ký tự")
        elif key == "description":
            value = clean_note(value)
            if value is not None and len(value) > DESCRIPTION_MAX_LENGTH:
                raise InvalidRewardError(f"Mô tả tối đa {DESCRIPTION_MAX_LENGTH} ký tự")
        elif key == "price_coins":
            value = validate_price(value)
        elif key == "per_user_limit" and value is not None and value < 1:
            raise InvalidRewardError("Giới hạn mỗi người phải từ 1")
        old = getattr(item, key)
        if old != value:
            diff[key] = {"from": old, "to": value}
            setattr(item, key, value)

    @staticmethod
    async def _apply_target(
        uow: RewardsUnitOfWork,
        item: RewardItem,
        key: str,
        value: Any,
        locked: bool,
        frame: AvatarFrame | None,
        diff: dict[str, dict[str, Any]],
    ) -> AvatarFrame | None:
        field = {"vip_days": ItemKind.VIP_DAYS, "ticket_count": ItemKind.VIP_TICKET}.get(
            key, ItemKind.AVATAR_FRAME
        )
        if item.kind is not field:
            raise InvalidRewardError("Trường này không thuộc loại của món")
        if key == "frame_code":
            new_frame = await resolve_shop_frame(uow, value)
            if new_frame.id != item.frame_id:
                if locked:
                    raise RewardItemLockedError()
                diff[key] = {"from": frame.code if frame else None, "to": new_frame.code}
                item.frame_id = new_frame.id
            return new_frame
        old = getattr(item, key)
        if old != value:
            if locked:
                raise RewardItemLockedError()
            diff[key] = {"from": old, "to": value}
            setattr(item, key, value)
        return frame
