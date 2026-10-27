from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import SystemSettingsView
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.application.system_settings import CachedSystemSettings, merge_settings
from app.modules.admin.domain.errors import (
    EmptySettingsChangeError,
    SamplePageInvalidError,
    UnknownSettingError,
)
from app.modules.admin.domain.system_settings import SETTING_SPECS, validate_setting
from app.modules.auth.application.public import Identity


class UpdateSystemSettingsUseCase:
    """F13.05, F13.06 — Đổi cấu hình hệ thống (US-QT-13).

    Kiểm kiểu/khoảng từng khóa, ghi giá trị và nhật ký trong một giao dịch, rồi xóa bộ đệm để có hiệu lực
    ngay. Giá trị sai thì từ chối cả lượt, không ghi gì. Giá trị `null` của một khóa nghĩa là "về mặc định":
    xóa dòng khỏi `system_settings` (với `sample_page_id`, mặc định là null nên trùng nghĩa "bỏ trang mẫu").
    """

    def __init__(
        self, uow_factory: Callable[[], AdminUnitOfWork], clock: Clock, settings: CachedSystemSettings
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._settings = settings

    async def execute(self, actor: Identity, changes: dict[str, Any]) -> SystemSettingsView:
        if not actor.is_admin:
            raise PermissionDeniedError()
        if not changes:
            raise EmptySettingsChangeError()
        resets = [key for key, raw in changes.items() if raw is None]
        unknown = [key for key in resets if key not in SETTING_SPECS]
        if unknown:
            raise UnknownSettingError(f"Khóa cấu hình không tồn tại: {unknown[0]}")
        validated = {key: validate_setting(key, raw) for key, raw in changes.items() if raw is not None}
        now = self._clock.now()
        async with self._uow_factory() as uow:
            sample_id = validated.get("sample_page_id")
            if sample_id is not None and not await uow.system_settings.is_valid_sample_page(int(sample_id)):
                raise SamplePageInvalidError()
            before, _ = merge_settings(self._settings.defaults, await uow.system_settings.load_all())
            await uow.system_settings.upsert_many(validated, actor.user_id, now)
            await uow.system_settings.delete_many(resets)
            old, default = before.as_dict(), self._settings.defaults.as_dict()
            diff = {key: {"from": old[key], "to": value} for key, value in validated.items()}
            diff.update({key: {"from": old[key], "to": default[key]} for key in resets})
            await uow.audit.add(
                actor.user_id, "settings.updated", "system_settings", None, {"changes": diff}, now
            )
            await uow.commit()
        self._settings.invalidate()
        return SystemSettingsView(await self._settings.snapshot(), await self._settings.overridden_keys())
