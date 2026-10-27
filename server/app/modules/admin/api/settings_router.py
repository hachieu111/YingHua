from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.modules.admin.api.schemas import (
    SamplePageCandidateList,
    SamplePageCandidateResponse,
    SystemSettingsResponse,
    SystemStatusResponse,
)
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.application.use_cases.get_system_settings import GetSystemSettingsUseCase
from app.modules.admin.application.use_cases.get_system_status import GetSystemStatusUseCase
from app.modules.admin.application.use_cases.list_sample_page_candidates import (
    ListSamplePageCandidatesUseCase,
)
from app.modules.admin.application.use_cases.update_system_settings import UpdateSystemSettingsUseCase
from app.modules.admin.domain.system_settings import MAINTENANCE_MESSAGE
from app.modules.admin.infrastructure.uow import SqlAdminUnitOfWork
from app.modules.auth.api.public import Identity, require_admin

admin_router = APIRouter(prefix="/admin/system-settings", tags=["M13 Cấu hình hệ thống"])
status_router = APIRouter(prefix="/system", tags=["M13 Cấu hình hệ thống"])


def _uow_factory(container: Container) -> Callable[[], AdminUnitOfWork]:
    def make() -> AdminUnitOfWork:
        return SqlAdminUnitOfWork(container.session_factory)

    return make


@admin_router.get("", response_model=SystemSettingsResponse, summary="Xem cấu hình hệ thống (F13.05)")
async def get_system_settings(
    admin: Identity = Depends(require_admin), container: Container = Depends(get_container)
) -> SystemSettingsResponse:
    view = await GetSystemSettingsUseCase(container.system_settings).execute(admin)
    return SystemSettingsResponse.from_view(view)


@admin_router.get(
    "/sample-page-candidates",
    response_model=SamplePageCandidateList,
    summary="Trang chọn được làm trang mẫu: truyện công khai, đã dịch xong (F13.05, F04.16)",
)
async def list_sample_page_candidates(
    admin: Identity = Depends(require_admin), container: Container = Depends(get_container)
) -> SamplePageCandidateList:
    items = await ListSamplePageCandidatesUseCase(_uow_factory(container)).execute(admin)
    return SamplePageCandidateList(items=[SamplePageCandidateResponse.from_item(i) for i in items])


@admin_router.patch(
    "",
    response_model=SystemSettingsResponse,
    summary="Đổi cấu hình hệ thống (F13.05)",
    description=(
        "Thân là đối tượng JSON {khóa: giá trị}, chỉ gửi khóa cần đổi. Giá trị sai kiểu/khoảng bị từ chối "
        "cả lượt (400 `INVALID_SETTING_VALUE`). Giá trị null đưa khóa về mặc định "
        "(với `sample_page_id` là bỏ trang mẫu)."
    ),
)
async def update_system_settings(
    changes: dict[str, Any],
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> SystemSettingsResponse:
    use_case = UpdateSystemSettingsUseCase(
        _uow_factory(container), container.clock, container.system_settings
    )
    return SystemSettingsResponse.from_view(await use_case.execute(admin, changes))


@status_router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Trạng thái công khai của hệ thống: bảo trì, LLM, TTS, trang mẫu (F13.05)",
)
async def get_system_status(container: Container = Depends(get_container)) -> SystemStatusResponse:
    status = await GetSystemStatusUseCase(container.system_settings).execute()
    return SystemStatusResponse.from_status(status, MAINTENANCE_MESSAGE)
