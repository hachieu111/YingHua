from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.modules.auth.api.public import Identity, get_identity
from app.modules.settings.api.schemas import SettingsResponse, UpdateSettingsRequest
from app.modules.settings.application.ports import SettingsUnitOfWork
from app.modules.settings.application.use_cases.get_settings import GetSettingsUseCase
from app.modules.settings.application.use_cases.update_settings import UpdateSettingsUseCase
from app.modules.settings.infrastructure.uow import SqlSettingsUnitOfWork

router = APIRouter(prefix="/settings", tags=["M02 Cài đặt cá nhân"])


def _uow_factory(container: Container) -> Callable[[], SettingsUnitOfWork]:
    def make() -> SettingsUnitOfWork:
        return SqlSettingsUnitOfWork(container.session_factory)

    return make


@router.get("", response_model=SettingsResponse, summary="Xem cài đặt cá nhân (F02.01–F02.03)")
async def get_settings(
    identity: Identity = Depends(get_identity), container: Container = Depends(get_container)
) -> SettingsResponse:
    use_case = GetSettingsUseCase(_uow_factory(container))
    return SettingsResponse.from_entity(await use_case.execute(identity))


@router.patch("", response_model=SettingsResponse, summary="Sửa cài đặt cá nhân (F02.01–F02.03)")
async def update_settings(
    body: UpdateSettingsRequest,
    identity: Identity = Depends(get_identity),
    container: Container = Depends(get_container),
) -> SettingsResponse:
    use_case = UpdateSettingsUseCase(_uow_factory(container), container.clock)
    changes = body.model_dump(exclude_unset=True)
    return SettingsResponse.from_entity(await use_case.execute(identity, changes))
