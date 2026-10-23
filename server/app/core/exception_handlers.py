"""Ánh xạ lỗi sang HTTP theo một định dạng duy nhất (xem .claude/rules/api-conventions.md)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import DomainError, ErrorKind

_STATUS_BY_KIND: dict[ErrorKind, int] = {
    ErrorKind.INVALID_INPUT: 400,
    ErrorKind.UNAUTHENTICATED: 401,
    ErrorKind.PERMISSION_DENIED: 403,
    ErrorKind.NOT_FOUND: 404,
    ErrorKind.CONFLICT: 409,
    ErrorKind.PAYLOAD_TOO_LARGE: 413,
    ErrorKind.RATE_LIMITED: 429,
    ErrorKind.EXTERNAL_SERVICE: 503,
}

_HTTP_CODES: dict[int, tuple[str, str]] = {
    401: ("UNAUTHENTICATED", "Bạn cần đăng nhập"),
    403: ("PERMISSION_DENIED", "Bạn không có quyền thực hiện thao tác này"),
    404: ("NOT_FOUND", "Không tìm thấy đường dẫn"),
    405: ("METHOD_NOT_ALLOWED", "Phương thức không được hỗ trợ"),
}


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def _domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    headers = {"WWW-Authenticate": "Bearer"} if exc.kind is ErrorKind.UNAUTHENTICATED else None
    return JSONResponse(
        status_code=_STATUS_BY_KIND[exc.kind],
        content=error_body(exc.code, exc.message, exc.details),
        headers=headers,
    )


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Chỉ trả vị trí + thông điệp, không trả lại giá trị người dùng gửi lên.
    fields = [
        {"loc": list(err.get("loc", ())), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body("VALIDATION_ERROR", "Dữ liệu gửi lên không hợp lệ", {"fields": fields}),
    )


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, message = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", str(exc.detail)))
    return JSONResponse(
        status_code=exc.status_code, content=error_body(code, message), headers=getattr(exc, "headers", None)
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
