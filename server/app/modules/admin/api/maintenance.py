"""Chế độ bảo trì (F13.05, US-QT-13 TC5): khi bật, mọi API trả 503 trừ quản trị viên và vài đường dẫn."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.errors import UnauthenticatedError
from app.core.exception_handlers import error_body
from app.modules.admin.domain.system_settings import MAINTENANCE_MESSAGE

log = logging.getLogger(__name__)

MAINTENANCE_CODE = "MAINTENANCE_MODE"
RETRY_AFTER_SECONDS = "60"
# Vẫn dùng được khi bảo trì: kiểm tra sống, đăng nhập/làm mới (để quản trị viên vào được),
# trạng thái công khai, tài liệu API.
_ALLOWED_SUFFIXES = (
    "/health",
    "/auth/login",
    "/auth/refresh",
    "/system/status",
    "/docs",
    "/openapi.json",
)


def _is_admin_request(request: Request) -> bool:
    """Chỉ để mở cổng bảo trì: đọc vai trò từ JWT đã ký; quyền thật vẫn do `require_admin` kiểm."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return False
    try:
        claims = request.app.state.container.tokens.decode_access_token(header[7:].strip())
    except UnauthenticatedError:
        return False
    return bool(claims.role == "admin")


async def maintenance_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    path = request.url.path
    if request.method == "OPTIONS" or path.endswith(_ALLOWED_SUFFIXES):
        return await call_next(request)
    container = getattr(request.app.state, "container", None)
    if container is None:
        return await call_next(request)
    try:
        enabled = (await container.system_settings.snapshot()).maintenance_mode
    except Exception:
        # Không đọc được cấu hình thì không chặn người dùng; lỗi thật sẽ lộ ở chính yêu cầu.
        log.warning("Không đọc được cấu hình bảo trì, bỏ qua kiểm tra", exc_info=True)
        return await call_next(request)
    if not enabled or _is_admin_request(request):
        return await call_next(request)
    return JSONResponse(
        status_code=503,
        content=error_body(MAINTENANCE_CODE, MAINTENANCE_MESSAGE),
        headers={"Retry-After": RETRY_AFTER_SECONDS},
    )
