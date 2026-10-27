from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.container import Container, get_container
from app.core.errors import PermissionDeniedError, UnauthenticatedError
from app.modules.auth.application.dto import AuthConfig, Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.application.session_issuer import SessionIssuer
from app.modules.auth.application.use_cases.authenticate import AuthenticateUseCase
from app.modules.auth.application.use_cases.change_password import ChangePasswordUseCase
from app.modules.auth.application.use_cases.get_profile import GetProfileUseCase
from app.modules.auth.application.use_cases.login import LoginUseCase
from app.modules.auth.application.use_cases.logout import LogoutUseCase
from app.modules.auth.application.use_cases.logout_all import LogoutAllUseCase
from app.modules.auth.application.use_cases.refresh_session import RefreshSessionUseCase
from app.modules.auth.application.use_cases.register import RegisterUseCase
from app.modules.auth.application.use_cases.remove_avatar import RemoveAvatarUseCase
from app.modules.auth.application.use_cases.request_password_reset import RequestPasswordResetUseCase
from app.modules.auth.application.use_cases.reset_password import ResetPasswordUseCase
from app.modules.auth.application.use_cases.set_avatar_preset import SetAvatarPresetUseCase
from app.modules.auth.application.use_cases.update_profile import UpdateProfileUseCase
from app.modules.auth.application.use_cases.upload_avatar import UploadAvatarUseCase
from app.modules.auth.infrastructure.email_outbox import FileOutboxEmailSender
from app.modules.auth.infrastructure.uow import SqlAuthUnitOfWork

bearer_scheme = HTTPBearer(auto_error=False, description="Mã truy cập (access token)")


@dataclass(slots=True)
class AuthServices:
    register: RegisterUseCase
    login: LoginUseCase
    refresh: RefreshSessionUseCase
    logout: LogoutUseCase
    logout_all: LogoutAllUseCase
    request_reset: RequestPasswordResetUseCase
    reset_password: ResetPasswordUseCase
    get_profile: GetProfileUseCase
    update_profile: UpdateProfileUseCase
    upload_avatar: UploadAvatarUseCase
    remove_avatar: RemoveAvatarUseCase
    set_avatar_preset: SetAvatarPresetUseCase
    change_password: ChangePasswordUseCase
    authenticate: AuthenticateUseCase


def _auth_config(container: Container) -> AuthConfig:
    s = container.settings
    return AuthConfig(
        refresh_ttl=timedelta(days=s.refresh_token_days),
        short_refresh_ttl=timedelta(hours=s.refresh_token_short_hours),
        reset_ttl=timedelta(minutes=s.password_reset_minutes),
        access_expires_in=s.access_token_minutes * 60,
        frontend_url=s.frontend_url,
        login_max_attempts_per_email=s.login_max_attempts_per_email,
        login_max_attempts_per_ip=s.login_max_attempts_per_ip,
    )


def build_auth_services(container: Container) -> AuthServices:
    config = _auth_config(container)

    def uow_factory() -> AuthUnitOfWork:
        return SqlAuthUnitOfWork(container.session_factory)

    clock, tokens = container.clock, container.tokens
    issuer = SessionIssuer(tokens, clock, config)
    email_sender = FileOutboxEmailSender(container.settings.storage_dir / "outbox")
    return AuthServices(
        register=RegisterUseCase(uow_factory, clock, issuer),
        login=LoginUseCase(uow_factory, clock, issuer, container.login_limiter, config),
        refresh=RefreshSessionUseCase(uow_factory, clock, issuer, config.short_refresh_ttl),
        logout=LogoutUseCase(uow_factory, clock),
        logout_all=LogoutAllUseCase(uow_factory, clock),
        request_reset=RequestPasswordResetUseCase(uow_factory, clock, email_sender, config),
        reset_password=ResetPasswordUseCase(uow_factory, clock),
        get_profile=GetProfileUseCase(uow_factory),
        update_profile=UpdateProfileUseCase(uow_factory),
        upload_avatar=UploadAvatarUseCase(uow_factory, clock, container.storage),
        remove_avatar=RemoveAvatarUseCase(uow_factory, container.storage),
        set_avatar_preset=SetAvatarPresetUseCase(uow_factory, container.storage),
        change_password=ChangePasswordUseCase(uow_factory, clock),
        authenticate=AuthenticateUseCase(uow_factory, clock, tokens),
    )


def get_auth_services(container: Container = Depends(get_container)) -> AuthServices:
    return build_auth_services(container)


async def get_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    services: AuthServices = Depends(get_auth_services),
) -> Identity:
    """Bắt buộc đăng nhập (F01.09)."""
    if credentials is None:
        raise UnauthenticatedError()
    return await services.authenticate.execute(credentials.credentials)


async def get_optional_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    services: AuthServices = Depends(get_auth_services),
) -> Identity | None:
    """Cho phép Khách (không gửi mã). Mã hỏng/hết hạn vẫn bị từ chối để giao diện làm mới phiên (F01.09)."""
    if credentials is None:
        return None
    return await services.authenticate.execute(credentials.credentials)


async def require_admin(identity: Identity = Depends(get_identity)) -> Identity:
    if not identity.is_admin:
        raise PermissionDeniedError()
    return identity


def client_info(request: Request) -> tuple[str | None, str | None]:
    """(user_agent, ip) của thiết bị gọi, để phân biệt phiên."""
    return request.headers.get("user-agent"), request.client.host if request.client else None


UowFactory = Callable[[], AuthUnitOfWork]
