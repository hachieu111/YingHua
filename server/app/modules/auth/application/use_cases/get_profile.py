from __future__ import annotations

from collections.abc import Callable

from app.core.errors import NotFoundError
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.entities import User


class GetProfileUseCase:
    """F01.07 (xem) — Hồ sơ của chính người gọi; không nhận mã người dùng từ tham số (US-NH-04)."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity) -> User:
        async with self._uow_factory() as uow:
            user = await uow.users.get(identity.user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy tài khoản")
        return user
