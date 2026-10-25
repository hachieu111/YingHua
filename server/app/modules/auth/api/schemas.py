from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.uploads import file_url
from app.modules.auth.application.dto import AuthResult, TokenPair
from app.modules.auth.domain.entities import User
from app.modules.auth.domain.rules import DISPLAY_NAME_MAX_LENGTH, PASSWORD_MAX_LENGTH

Password = Field(max_length=PASSWORD_MAX_LENGTH)


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Password
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Password


class RefreshRequest(BaseModel):
    refresh_token: str = Field(max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(max_length=200)
    new_password: str = Password


class ChangePasswordRequest(BaseModel):
    current_password: str = Password
    new_password: str = Password


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)
    chinese_name: str | None = Field(default=None, max_length=64)
    show_email: bool | None = None
    show_join_date: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    chinese_name: str | None
    avatar_url: str | None
    role: str
    status: str
    show_email: bool
    show_join_date: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            chinese_name=user.chinese_name,
            avatar_url=file_url(user.avatar_file_id),
            role=user.role.value,
            status=user.status.value,
            show_email=user.show_email,
            show_join_date=user.show_join_date,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

    @classmethod
    def from_pair(cls, pair: TokenPair) -> TokenResponse:
        return cls(
            access_token=pair.access_token, refresh_token=pair.refresh_token, expires_in=pair.expires_in
        )


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse

    @classmethod
    def from_result(cls, result: AuthResult) -> AuthResponse:
        return cls(user=UserResponse.from_entity(result.user), tokens=TokenResponse.from_pair(result.tokens))


class MessageResponse(BaseModel):
    message: str


class LogoutAllResponse(BaseModel):
    revoked_sessions: int
