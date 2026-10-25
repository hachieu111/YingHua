from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.settings.application.ports import SettingsUnitOfWork
from app.modules.settings.domain.entities import UserSettings


class GetSettingsUseCase:
    """F02.01–F02.03 (xem) — Cài đặt của chủ sở hữu; chưa có thì dùng mặc định.

    Quản trị viên xem được của người khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], SettingsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, owner_id: int | None = None) -> UserSettings:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            settings = await uow.settings.get_or_create(owner)
            await uow.commit()
        return settings
