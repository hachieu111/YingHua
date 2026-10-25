from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.auth.application.public import User


class AdminUserResponse(BaseModel):
    """Không có mật khẩu (kể cả bản băm) hay dữ liệu học tập riêng."""

    id: int
    email: str
    display_name: str
    role: str
    status: str
    locked_reason: str | None
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_entity(cls, u: User) -> AdminUserResponse:
        return cls(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=u.role.value,
            status=u.status.value,
            locked_reason=u.locked_reason,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )


class AdminUserPage(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int


class ChangeRoleRequest(BaseModel):
    role: Literal["user", "admin"]


class LockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
