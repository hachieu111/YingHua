from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.api.public import Identity, get_identity, get_optional_identity, require_admin
from app.modules.imaging.api.dependencies import ImagingServices, get_imaging_services
from app.modules.imaging.api.schemas import (
    AdminTranslationPage,
    PageStatusResponse,
    RequeueResponse,
)
from app.modules.imaging.domain.entities import ImageVariant, TranslationStatus
from app.modules.imaging.domain.rules import ascii_filename

router = APIRouter(tags=["M04 Xử lý ảnh"])
admin_router = APIRouter(prefix="/admin/translations", tags=["M04 Xử lý ảnh"])


@router.get(
    "/pages/{page_id}/status",
    response_model=PageStatusResponse,
    summary="Trạng thái xử lý của trang (F04.02)",
)
async def get_page_status(
    page_id: int,
    identity: Identity | None = Depends(get_optional_identity),
    services: ImagingServices = Depends(get_imaging_services),
) -> PageStatusResponse:
    return PageStatusResponse.from_status(await services.page_status.execute(identity, page_id))


@router.post(
    "/pages/{page_id}/retranslate",
    response_model=RequeueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dịch lại trang bị lỗi (F04.03)",
)
async def retranslate_page(
    page_id: int,
    identity: Identity = Depends(get_identity),
    services: ImagingServices = Depends(get_imaging_services),
) -> RequeueResponse:
    return RequeueResponse.from_result(await services.retranslate.execute(identity, page_id))


@router.get(
    "/pages/{page_id}/download",
    summary="Tải ảnh của trang về máy (F04.04)",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}, "description": "Tệp ảnh đính kèm"}},
)
async def download_page_image(
    page_id: int,
    variant: Literal["original", "inpainted", "rendered"] = Query(default="rendered"),
    identity: Identity | None = Depends(get_optional_identity),
    services: ImagingServices = Depends(get_imaging_services),
) -> Response:
    image = await services.download.execute(identity, page_id, ImageVariant(variant))
    disposition = (
        f"attachment; filename=\"{ascii_filename(image.filename)}\"; filename*=UTF-8''{quote(image.filename)}"
    )
    return Response(
        content=image.data,
        media_type=image.mime_type,
        headers={
            "Content-Disposition": disposition,
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@admin_router.get("", response_model=AdminTranslationPage, summary="Giám sát hàng đợi xử lý ảnh (F04.05)")
async def list_translations(
    status_filter: Literal["queued", "running", "done", "failed"] | None = Query(
        default=None, alias="status", description="Lọc theo trạng thái"
    ),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: Identity = Depends(require_admin),
    services: ImagingServices = Depends(get_imaging_services),
) -> AdminTranslationPage:
    wanted = TranslationStatus(status_filter) if status_filter else None
    result = await services.list_translations.execute(admin, wanted, page, size)
    return AdminTranslationPage.from_list(result, page, size)


@admin_router.post(
    "/{translation_id}/retry",
    response_model=RequeueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Chạy lại bản dịch lỗi (F04.06)",
)
async def retry_translation(
    translation_id: int,
    admin: Identity = Depends(require_admin),
    services: ImagingServices = Depends(get_imaging_services),
) -> RequeueResponse:
    return RequeueResponse.from_result(await services.retry.execute(admin, translation_id))
