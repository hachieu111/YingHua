from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.entities import AvatarFrame


class ListAdminFramesUseCase:
    """F17.09 - Mọi khung đang dùng cho form món đổi thưởng, không phụ thuộc ví của quản trị viên."""

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity) -> list[AvatarFrame]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            return await uow.wallets.list_frames()
