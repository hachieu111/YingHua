from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import AdminItemView, CreateItemCommand
from app.modules.rewards.application.item_rules import resolve_shop_frame
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.entities import ItemKind, NewRewardItem
from app.modules.rewards.domain.errors import InvalidRewardError, RewardItemCodeTakenError
from app.modules.rewards.domain.rules import (
    clean_note,
    validate_item_code,
    validate_item_kind_fields,
    validate_price,
)

NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 255


class CreateRewardItemUseCase:
    """F17.09 - Thêm món vào cửa hàng đổi thưởng (US-QT-17).

    Giá 1-100.000 xu; ngày VIP 1-365; vé 1-10; khung phải tồn tại và là khung bán ở cửa hàng (không phải
    khung thưởng mùa hay khung VIP). Ghi nhật ký `reward_item.created` trong cùng giao dịch.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, actor: Identity, command: CreateItemCommand) -> AdminItemView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        try:
            kind = ItemKind(command.kind)
        except ValueError as exc:
            raise InvalidRewardError("Loại món không hợp lệ") from exc
        name = " ".join(command.name.split())
        if not name or len(name) > NAME_MAX_LENGTH:
            raise InvalidRewardError(f"Tên món từ 1 đến {NAME_MAX_LENGTH} ký tự")
        description = clean_note(command.description)
        if description is not None and len(description) > DESCRIPTION_MAX_LENGTH:
            raise InvalidRewardError(f"Mô tả tối đa {DESCRIPTION_MAX_LENGTH} ký tự")
        if command.per_user_limit is not None and command.per_user_limit < 1:
            raise InvalidRewardError("Giới hạn mỗi người phải từ 1")
        code, price = validate_item_code(command.code), validate_price(command.price_coins)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            if await uow.shop.get_item_by_code(code) is not None:
                raise RewardItemCodeTakenError()
            frame = await resolve_shop_frame(uow, command.frame_code) if command.frame_code else None
            frame_id = frame.id if frame else None
            validate_item_kind_fields(kind, command.vip_days, command.ticket_count, frame_id)
            item = await uow.shop.add_item(
                NewRewardItem(
                    code=code,
                    name=name,
                    description=description,
                    kind=kind,
                    price_coins=price,
                    vip_days=command.vip_days,
                    ticket_count=command.ticket_count,
                    frame_id=frame_id,
                    per_user_limit=command.per_user_limit,
                    is_active=command.is_active,
                    sort_order=command.sort_order,
                    updated_by=actor.user_id,
                    created_at=now,
                )
            )
            await uow.audit.add(
                actor.user_id,
                "reward_item.created",
                "reward_item",
                item.id,
                {"code": code, "kind": kind.value, "price_coins": price},
                now,
            )
            await uow.commit()
        return AdminItemView(item, frame, False)
