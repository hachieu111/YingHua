from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.errors import InvalidInputError, NotFoundError
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.entities import User
from app.modules.auth.domain.rules import clean_display_name

CHINESE_NAME_MAX_LENGTH = 32


class UpdateProfileUseCase:
    """F01.07 (sửa) — Sửa hồ sơ của chính mình (US-NH-04). Chỉ cập nhật các trường có trong `changes`."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, changes: dict[str, Any]) -> User:
        async with self._uow_factory() as uow:
            user = await uow.users.get(identity.user_id)
            if user is None:
                raise NotFoundError("Không tìm thấy tài khoản")
            if "display_name" in changes:
                user.display_name = clean_display_name(str(changes["display_name"] or ""))
            if "chinese_name" in changes:
                value = (changes["chinese_name"] or "").strip()
                if len(value) > CHINESE_NAME_MAX_LENGTH:
                    raise InvalidInputError("Tên tiếng Trung tối đa 32 ký tự")
                user.chinese_name = value or None
            for flag in ("show_email", "show_join_date"):
                if flag in changes and changes[flag] is not None:
                    setattr(user, flag, bool(changes[flag]))
            await uow.users.update(user)
            await uow.commit()
        return user
