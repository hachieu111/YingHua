from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Query

from app.container import Container, get_container
from app.modules.admin.api.schemas import AdminUserPage, AdminUserResponse, ChangeRoleRequest, LockRequest
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.admin.application.use_cases.change_user_role import ChangeUserRoleUseCase
from app.modules.admin.application.use_cases.list_users import ListUsersUseCase
from app.modules.admin.application.use_cases.set_user_lock import SetUserLockUseCase
from app.modules.admin.infrastructure.uow import SqlAdminUnitOfWork
from app.modules.auth.api.public import Identity, require_admin
from app.modules.auth.application.public import Role

router = APIRouter(prefix="/admin/users", tags=["M13 Quản trị người dùng"])


def _uow_factory(container: Container) -> Callable[[], AdminUnitOfWork]:
    def make() -> AdminUnitOfWork:
        return SqlAdminUnitOfWork(container.session_factory)

    return make


@router.get("", response_model=AdminUserPage, summary="Xem và tìm người dùng (F13.01)")
async def list_users(
    q: str | None = Query(default=None, max_length=100, description="Một phần email"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> AdminUserPage:
    users, total = await ListUsersUseCase(_uow_factory(container)).execute(admin, q, page, size)
    return AdminUserPage(
        items=[AdminUserResponse.from_entity(u) for u in users], total=total, page=page, size=size
    )


@router.patch("/{user_id}/role", response_model=AdminUserResponse, summary="Đổi vai trò người dùng (F13.02)")
async def change_role(
    user_id: int,
    body: ChangeRoleRequest,
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> AdminUserResponse:
    use_case = ChangeUserRoleUseCase(_uow_factory(container), container.clock)
    return AdminUserResponse.from_entity(await use_case.execute(admin, user_id, Role(body.role)))


@router.post("/{user_id}/lock", response_model=AdminUserResponse, summary="Khóa tài khoản (F13.03)")
async def lock_user(
    user_id: int,
    body: LockRequest,
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> AdminUserResponse:
    use_case = SetUserLockUseCase(_uow_factory(container), container.clock)
    return AdminUserResponse.from_entity(await use_case.execute(admin, user_id, True, body.reason))


@router.post("/{user_id}/unlock", response_model=AdminUserResponse, summary="Mở khóa tài khoản (F13.03)")
async def unlock_user(
    user_id: int,
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> AdminUserResponse:
    use_case = SetUserLockUseCase(_uow_factory(container), container.clock)
    return AdminUserResponse.from_entity(await use_case.execute(admin, user_id, False, None))
