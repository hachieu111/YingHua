"""Quản trị viên xem và sửa dữ liệu đọc truyện của người dùng khác (F13.07, US-QT-14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.reader.api.dependencies import ReaderServices, get_reader_services
from app.modules.reader.api.schemas import (
    AnnotationResponse,
    BookmarkPageResponse,
    BubbleEditResponse,
    SaveAnnotationsRequest,
)

admin_router = APIRouter(prefix="/admin/users/{user_id}", tags=["M13 Quản trị"])


@admin_router.get(
    "/bookmarks",
    response_model=BookmarkPageResponse,
    summary="Quản trị: trang đã lưu của người dùng (F13.07)",
)
async def admin_list_bookmarks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReaderServices = Depends(get_reader_services),
) -> BookmarkPageResponse:
    result = await services.list_bookmarks.execute(admin, page, size, user_id)
    return BookmarkPageResponse.from_page(result, page, size)


@admin_router.get(
    "/pages/{page_id}/annotations",
    response_model=AnnotationResponse | None,
    summary="Quản trị: ghi chú trên trang của người dùng; null nếu chưa có (F13.07)",
)
async def admin_get_annotations(
    page_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReaderServices = Depends(get_reader_services),
) -> AnnotationResponse | None:
    annotation = await services.get_annotations.execute(admin, page_id, user_id)
    return AnnotationResponse.from_entity(annotation) if annotation else None


@admin_router.put(
    "/pages/{page_id}/annotations",
    response_model=AnnotationResponse,
    summary="Quản trị: thay ghi chú trên trang của người dùng; ghi nhật ký (F13.07)",
)
async def admin_save_annotations(
    page_id: int,
    body: SaveAnnotationsRequest,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReaderServices = Depends(get_reader_services),
) -> AnnotationResponse:
    annotation = await services.save_annotations.execute(admin, page_id, body.to_input(), user_id)
    return AnnotationResponse.from_entity(annotation)


@admin_router.delete(
    "/pages/{page_id}/annotations",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quản trị: xóa ghi chú trên trang của người dùng; ghi nhật ký (F13.07)",
)
async def admin_clear_annotations(
    page_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReaderServices = Depends(get_reader_services),
) -> Response:
    await services.clear_annotations.execute(admin, page_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get(
    "/bubble-edits",
    response_model=list[BubbleEditResponse],
    summary="Quản trị: bản sửa dịch riêng của người dùng trên một trang (F13.07)",
)
async def admin_list_bubble_edits(
    page_id: int = Query(ge=1),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReaderServices = Depends(get_reader_services),
) -> list[BubbleEditResponse]:
    edits = await services.list_edits.execute(admin, page_id, user_id)
    return [BubbleEditResponse.from_edited(e) for e in edits]


@admin_router.delete(
    "/bubbles/{bubble_id}/edit",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quản trị: hoàn tác bản sửa dịch của người dùng; ghi nhật ký (F13.07)",
)
async def admin_delete_bubble_edit(
    bubble_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReaderServices = Depends(get_reader_services),
) -> Response:
    await services.delete_edit.execute(admin, bubble_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
