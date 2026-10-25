"""Quản trị viên xem Thư viện, tiến độ đọc và ảnh tải nhanh của người dùng khác (F13.07, US-QT-14).

Sửa/xóa truyện riêng của người dùng dùng lại `PATCH/DELETE /series/{id}` (F03.11), đã ghi nhật ký.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.library.api.dependencies import LibraryServices, get_library_services
from app.modules.library.api.schemas import (
    ContinueItemResponse,
    PageResponse,
    QuickUploadPage,
    SeriesPage,
    SeriesResponse,
)
from app.modules.library.domain.entities import LibraryTab

admin_router = APIRouter(prefix="/admin/users/{user_id}", tags=["M13 Quản trị"])

MAX_PROGRESS_ITEMS = 50


@admin_router.get(
    "/library", response_model=SeriesPage, summary="Quản trị: Thư viện của người dùng theo tab (F13.07)"
)
async def admin_list_library(
    tab: Literal["all", "reading", "favorites", "completed"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesPage:
    result = await services.list_library.execute(admin, LibraryTab(tab), page, size, user_id)
    return SeriesPage(
        items=[SeriesResponse.from_view(v) for v in result.items], total=result.total, page=page, size=size
    )


@admin_router.get(
    "/reading-progress",
    response_model=list[ContinueItemResponse],
    summary="Quản trị: tiến độ đọc dở của người dùng (F13.07)",
)
async def admin_list_reading_progress(
    limit: int = Query(default=20, ge=1, le=MAX_PROGRESS_ITEMS),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: LibraryServices = Depends(get_library_services),
) -> list[ContinueItemResponse]:
    items = await services.list_continue.execute(admin, limit, user_id)
    return [ContinueItemResponse.from_item(i) for i in items]


@admin_router.get(
    "/quick-uploads",
    response_model=QuickUploadPage,
    summary="Quản trị: ảnh tải nhanh của người dùng (F13.07)",
)
async def admin_list_quick_uploads(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: LibraryServices = Depends(get_library_services),
) -> QuickUploadPage:
    result = await services.list_quick_uploads.execute(admin, page, size, user_id)
    return QuickUploadPage(
        items=[PageResponse.from_view(v) for v in result.items], total=result.total, page=page, size=size
    )
