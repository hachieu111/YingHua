from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status

from app.container import Container, get_container
from app.core.uploads import read_image_upload
from app.modules.auth.api.dependencies import AuthServices, client_info, get_auth_services, get_identity
from app.modules.auth.api.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutAllResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserResponse,
)
from app.modules.auth.application.dto import Identity

auth_router = APIRouter(prefix="/auth", tags=["M01 Xác thực"])
account_router = APIRouter(prefix="/account", tags=["M01 Tài khoản"])


@auth_router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản (F01.01)",
)
async def register(
    body: RegisterRequest, request: Request, services: AuthServices = Depends(get_auth_services)
) -> AuthResponse:
    user_agent, ip = client_info(request)
    result = await services.register.execute(body.email, body.password, body.display_name, user_agent, ip)
    return AuthResponse.from_result(result)


@auth_router.post("/login", response_model=AuthResponse, summary="Đăng nhập (F01.02)")
async def login(
    body: LoginRequest, request: Request, services: AuthServices = Depends(get_auth_services)
) -> AuthResponse:
    user_agent, ip = client_info(request)
    return AuthResponse.from_result(await services.login.execute(body.email, body.password, user_agent, ip))


@auth_router.post("/refresh", response_model=AuthResponse, summary="Làm mới phiên đăng nhập (F01.03)")
async def refresh(
    body: RefreshRequest, request: Request, services: AuthServices = Depends(get_auth_services)
) -> AuthResponse:
    user_agent, ip = client_info(request)
    return AuthResponse.from_result(await services.refresh.execute(body.refresh_token, user_agent, ip))


@auth_router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Đăng xuất thiết bị hiện tại (F01.04)"
)
async def logout(
    identity: Identity = Depends(get_identity), services: AuthServices = Depends(get_auth_services)
) -> Response:
    await services.logout.execute(identity)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})


@auth_router.post("/logout-all", response_model=LogoutAllResponse, summary="Đăng xuất mọi thiết bị (F01.05)")
async def logout_all(
    identity: Identity = Depends(get_identity), services: AuthServices = Depends(get_auth_services)
) -> LogoutAllResponse:
    return LogoutAllResponse(revoked_sessions=await services.logout_all.execute(identity))


@auth_router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Yêu cầu liên kết đặt lại mật khẩu (F01.06)",
)
async def forgot_password(
    body: ForgotPasswordRequest, services: AuthServices = Depends(get_auth_services)
) -> MessageResponse:
    await services.request_reset.execute(body.email)
    return MessageResponse(message="Nếu email tồn tại, chúng tôi đã gửi hướng dẫn")


@auth_router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đặt mật khẩu mới bằng mã trong liên kết (F01.06)",
)
async def reset_password(
    body: ResetPasswordRequest, services: AuthServices = Depends(get_auth_services)
) -> Response:
    await services.reset_password.execute(body.token, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@account_router.get("/me", response_model=UserResponse, summary="Xem hồ sơ của tôi (F01.07)")
async def get_me(
    identity: Identity = Depends(get_identity), services: AuthServices = Depends(get_auth_services)
) -> UserResponse:
    return UserResponse.from_entity(await services.get_profile.execute(identity))


@account_router.patch("/me", response_model=UserResponse, summary="Sửa hồ sơ của tôi (F01.07)")
async def update_me(
    body: UpdateProfileRequest,
    identity: Identity = Depends(get_identity),
    services: AuthServices = Depends(get_auth_services),
) -> UserResponse:
    changes = body.model_dump(exclude_unset=True)
    return UserResponse.from_entity(await services.update_profile.execute(identity, changes))


@account_router.post(
    "/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Đổi mật khẩu (F01.08)"
)
async def change_password(
    body: ChangePasswordRequest,
    identity: Identity = Depends(get_identity),
    services: AuthServices = Depends(get_auth_services),
) -> Response:
    await services.change_password.execute(identity, body.current_password, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@account_router.post(
    "/me/avatar",
    response_model=UserResponse,
    summary="Tải ảnh đại diện (F01.10)",
    description="Nhận ảnh jpg/png/webp tối đa theo MAX_UPLOAD_MB; ảnh mới thay ảnh cũ.",
)
async def upload_avatar(
    file: UploadFile = File(description="Ảnh đại diện"),
    identity: Identity = Depends(get_identity),
    services: AuthServices = Depends(get_auth_services),
    container: Container = Depends(get_container),
) -> UserResponse:
    upload = await read_image_upload(file, container.settings.max_upload_mb * 1024 * 1024)
    return UserResponse.from_entity(await services.upload_avatar.execute(identity, upload))


@account_router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa ảnh đại diện (F01.10)",
    description="Gỡ ảnh đại diện và xóa tệp; chưa có ảnh thì vẫn trả 204.",
)
async def remove_avatar(
    identity: Identity = Depends(get_identity),
    services: AuthServices = Depends(get_auth_services),
) -> Response:
    await services.remove_avatar.execute(identity)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
