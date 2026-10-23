"""GET /api/v1/health — kiểm tra API và kết nối CSDL (rules/monitoring.md).

Đây là endpoint hạ tầng, không có nghiệp vụ nên không qua use case.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.container import Container, get_container

router = APIRouter(tags=["Hệ thống"])
log = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra tình trạng API và CSDL",
    responses={503: {"model": HealthResponse}},
)
async def health(container: Container = Depends(get_container)) -> HealthResponse | JSONResponse:
    try:
        async with container.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        log.exception("Không kết nối được CSDL")
        body = HealthResponse(status="degraded", database="error")
        return JSONResponse(status_code=503, content=body.model_dump())
    return HealthResponse(status="ok", database="ok")
