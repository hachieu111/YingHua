from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.settings.application.ports import SettingsUnitOfWork
from app.modules.settings.domain.entities import UserSettings, apply_changes


class UpdateSettingsUseCase:
    """F02.01 trình độ HSK (US-NH-06), F02.02 chế độ Đọc/Học (US-NH-07), F02.03 giọng đọc (US-NH-08).

    Quản trị viên sửa được cài đặt của người khác qua `owner_id` và việc đó được ghi nhật ký (F13.07, F13.06).
    """

    def __init__(self, uow_factory: Callable[[], SettingsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(
        self, identity: Identity, changes: dict[str, Any], owner_id: int | None = None
    ) -> UserSettings:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            settings = await uow.settings.get_or_create(owner)
            apply_changes(settings, changes)
            await uow.settings.save(settings)
            await record_admin_action(
                uow.audit,
                identity,
                owner,
                "settings.update",
                "user_settings",
                owner,
                self._clock.now(),
                {"fields": sorted(changes)},
            )
            await uow.commit()
        return settings
