from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import UploadItem
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.application.system_settings import SystemSettingsPort
from app.modules.auth.application.public import Identity


class ListModerationUploadsUseCase:
    """F13.04, F13.05 — Hàng chờ kiểm duyệt: ảnh mới tải lên kèm người tải (US-QT-12 TC1).

    Kiểm duyệt tự động bật thì gắn cờ nghi vấn theo luật đơn giản (kích thước, ảnh trùng, xử lý lỗi);
    tắt thì không gắn cờ và bộ lọc `flagged_only` trả danh sách rỗng (US-QT-13 TC6).
    """

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork], settings: SystemSettingsPort) -> None:
        self._uow_factory = uow_factory
        self._settings = settings

    async def execute(
        self, actor: Identity, flagged_only: bool, page: int, size: int
    ) -> tuple[list[UploadItem], int]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        auto = (await self._settings.snapshot()).auto_moderation_enabled
        if flagged_only and not auto:
            return [], 0
        async with self._uow_factory() as uow:
            return await uow.moderation.list_uploads(auto, flagged_only, (page - 1) * size, size)
