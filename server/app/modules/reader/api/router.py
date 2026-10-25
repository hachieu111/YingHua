from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.api.public import Identity, get_identity, get_optional_identity
from app.modules.reader.api.dependencies import (
    GUEST_SESSION_HEADER,
    ReaderServices,
    get_guest_session_id,
    get_reader_services,
)
from app.modules.reader.api.schemas import (
    AnnotationResponse,
    BookmarkPageResponse,
    BookmarkResponse,
    BubbleEditResponse,
    BubbleLookupResponse,
    ReadingResponse,
    SaveAnnotationsRequest,
    SaveBubbleEditRequest,
    SetBookmarkRequest,
)

router = APIRouter(tags=["M05 Đọc truyện"])


@router.get(
    "/pages/{page_id}/reading",
    response_model=ReadingResponse,
    summary="Dữ liệu đọc trang: ba dạng ảnh, bong bóng, ghi chú (F05.01)",
)
async def get_reading(
    page_id: int,
    identity: Identity | None = Depends(get_optional_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> ReadingResponse:
    return ReadingResponse.from_view(await services.get_reading.execute(identity, page_id))


@router.get(
    "/bubbles/{bubble_id}/lookup",
    response_model=BubbleLookupResponse,
    summary="Hover & Dịch: tra một từ trong bong bóng (F05.02, F05.03, F05.04)",
    description=(
        "Khách gửi kèm header `X-Guest-Session` (UUID) để tính hạn mức; chưa có thì máy chủ cấp phiên mới "
        "(trả trong thân và header). Hết hạn mức → 429 `GUEST_LOOKUP_LIMIT_REACHED`."
    ),
)
async def lookup_bubble_word(
    bubble_id: int,
    response: Response,
    word: str = Query(min_length=1, max_length=64, description="Từ tiếng Trung cần tra, nằm trong bong bóng"),
    identity: Identity | None = Depends(get_optional_identity),
    guest_session: uuid.UUID | None = Depends(get_guest_session_id),
    services: ReaderServices = Depends(get_reader_services),
) -> BubbleLookupResponse:
    result = await services.lookup.execute(identity, guest_session, bubble_id, word)
    if result.guest is not None:
        response.headers[GUEST_SESSION_HEADER] = result.guest.session_id
    return BubbleLookupResponse.from_lookup(result)


@router.put(
    "/bubbles/{bubble_id}/edit",
    response_model=BubbleEditResponse,
    summary="Sửa bản dịch riêng của một bong bóng (F05.05)",
)
async def save_bubble_edit(
    bubble_id: int,
    body: SaveBubbleEditRequest,
    identity: Identity = Depends(get_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> BubbleEditResponse:
    return BubbleEditResponse.from_edited(await services.save_edit.execute(identity, bubble_id, body.text_vi))


@router.delete(
    "/bubbles/{bubble_id}/edit",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hoàn tác bản sửa dịch (F05.06)",
)
async def delete_bubble_edit(
    bubble_id: int,
    identity: Identity = Depends(get_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> Response:
    await services.delete_edit.execute(identity, bubble_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/pages/{page_id}/bookmark",
    response_model=BookmarkResponse,
    summary="Đánh dấu / bỏ đánh dấu trang đã lưu (F05.07)",
)
async def set_bookmark(
    page_id: int,
    body: SetBookmarkRequest,
    identity: Identity = Depends(get_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> BookmarkResponse:
    annotation = await services.set_bookmark.execute(identity, page_id, body.is_bookmarked)
    return BookmarkResponse(page_id=page_id, is_bookmarked=annotation.is_bookmarked)


@router.get("/bookmarks", response_model=BookmarkPageResponse, summary="Danh sách trang đã lưu (F05.07)")
async def list_bookmarks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> BookmarkPageResponse:
    return BookmarkPageResponse.from_page(
        await services.list_bookmarks.execute(identity, page, size), page, size
    )


@router.put(
    "/pages/{page_id}/annotations",
    response_model=AnnotationResponse,
    summary="Lưu ghi chú trên trang: tô màu và nét vẽ (F05.08)",
)
async def save_annotations(
    page_id: int,
    body: SaveAnnotationsRequest,
    identity: Identity = Depends(get_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> AnnotationResponse:
    annotation = await services.save_annotations.execute(identity, page_id, body.to_input())
    return AnnotationResponse.from_entity(annotation)


@router.delete(
    "/pages/{page_id}/annotations",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa ghi chú trên trang, giữ dấu trang (F05.08)",
)
async def clear_annotations(
    page_id: int,
    identity: Identity = Depends(get_identity),
    services: ReaderServices = Depends(get_reader_services),
) -> Response:
    await services.clear_annotations.execute(identity, page_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
