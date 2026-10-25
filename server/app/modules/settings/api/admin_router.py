"""Quản trị viên xem và sửa cài đặt của người dùng khác (F13.07, US-QT-14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.settings.api.router import _uow_factory
from app.modules.settings.api.schemas import SettingsResponse, UpdateSettingsRequest
from app.modules.settings.application.use_cases.get_settings import GetSettingsUseCase
from app.modules.settings.application.use_cases.update_settings import UpdateSettingsUseCase

admin_router = APIRouter(prefix="/admin/users/{user_id}/settings", tags=["M13 Quản trị"])


@admin_router.get(
    "", response_model=SettingsResponse, summary="Quản trị: xem cài đặt của người dùng (F13.07)"
)
async def admin_get_settings(
    target_user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> SettingsResponse:
    use_case = GetSettingsUseCase(_uow_factory(container))
    return SettingsResponse.from_entity(await use_case.execute(admin, target_user_id))


@admin_router.patch(
    "",
    response_model=SettingsResponse,
    summary="Quản trị: sửa cài đặt của người dùng, có ghi nhật ký (F13.07)",
)
async def admin_update_settings(
    body: UpdateSettingsRequest,
    target_user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> SettingsResponse:
    use_case = UpdateSettingsUseCase(_uow_factory(container), container.clock)
    changes = body.model_dump(exclude_unset=True)
    return SettingsResponse.from_entity(await use_case.execute(admin, changes, target_user_id))
