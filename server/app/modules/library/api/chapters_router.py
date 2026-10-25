from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.core.uploads import read_image_upload, read_image_uploads
from app.modules.auth.api.public import Identity, get_identity, get_optional_identity
from app.modules.library.api.dependencies import LibraryServices, get_library_services
from app.modules.library.api.schemas import (
    ChapterDetailResponse,
    ChapterResponse,
    PageResponse,
    ProgressResponse,
    QuickUploadPage,
    SaveProgressRequest,
    UpdateChapterRequest,
    UploadItemResponse,
    UploadPagesResponse,
)
from app.modules.library.application.dto import ProgressInput
from app.modules.library.domain.errors import TooManyFilesError
from app.modules.library.domain.rules import MAX_FILES_PER_UPLOAD

router = APIRouter(tags=["M03 Thư viện"])


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterDetailResponse,
    summary="Chi tiết chương và danh sách trang (F03.03, F04.02)",
)
async def get_chapter(
    chapter_id: int,
    identity: Identity | None = Depends(get_optional_identity),
    services: LibraryServices = Depends(get_library_services),
) -> ChapterDetailResponse:
    return ChapterDetailResponse.from_detail(await services.get_chapter.execute(identity, chapter_id))


@router.patch(
    "/chapters/{chapter_id}", response_model=ChapterResponse, summary="Sửa chương (F03.09, F03.05, F03.11)"
)
async def update_chapter(
    chapter_id: int,
    body: UpdateChapterRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> ChapterResponse:
    changes = body.model_dump(exclude_unset=True)
    return ChapterResponse.from_chapter(await services.update_chapter.execute(identity, chapter_id, changes))


@router.delete(
    "/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa chương (F03.09, F03.11)"
)
async def delete_chapter(
    chapter_id: int,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> Response:
    await services.delete_chapter.execute(identity, chapter_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/chapters/{chapter_id}/pages",
    response_model=UploadPagesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải ảnh trang lên chương (F03.07)",
    description="Nhận nhiều ảnh (trường `files`); kết quả trả riêng từng tệp, tệp lỗi không chặn tệp khác",
)
async def upload_pages(
    chapter_id: int,
    files: list[UploadFile] = File(description="Các ảnh jpg/png/webp"),
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> UploadPagesResponse:
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise TooManyFilesError()
    attempts = await read_image_uploads(files, services.max_upload_bytes)
    results = await services.upload_pages.execute(identity, chapter_id, attempts)
    return UploadPagesResponse(
        results=[UploadItemResponse.from_result(r) for r in results],
        created=sum(1 for r in results if r.page is not None),
    )


@router.put(
    "/chapters/{chapter_id}/progress",
    response_model=ProgressResponse,
    summary="Lưu tiến độ đọc của chương (F03.12)",
)
async def save_progress(
    chapter_id: int,
    body: SaveProgressRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> ProgressResponse:
    data = ProgressInput(page_no=body.page_no, mode=body.mode, completed=body.completed)
    return ProgressResponse.from_progress(await services.save_progress.execute(identity, chapter_id, data))


@router.post(
    "/quick-uploads",
    response_model=PageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải nhanh một ảnh lẻ (F03.08)",
)
async def quick_upload(
    file: UploadFile = File(description="Ảnh jpg/png/webp"),
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> PageResponse:
    upload = await read_image_upload(file, services.max_upload_bytes)
    return PageResponse.from_view(await services.quick_upload.execute(identity, upload))


@router.get("/quick-uploads", response_model=QuickUploadPage, summary="Ảnh tải lên của tôi (F03.13, F03.08)")
async def list_quick_uploads(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> QuickUploadPage:
    result = await services.list_quick_uploads.execute(identity, page, size)
    return QuickUploadPage(
        items=[PageResponse.from_view(v) for v in result.items], total=result.total, page=page, size=size
    )


@router.get("/pages/{page_id}", response_model=PageResponse, summary="Chi tiết trang (F03.10, F04.02)")
async def get_page(
    page_id: int,
    identity: Identity | None = Depends(get_optional_identity),
    services: LibraryServices = Depends(get_library_services),
) -> PageResponse:
    return PageResponse.from_view(await services.get_page.execute(identity, page_id))


@router.delete(
    "/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa trang (F03.09, F03.11)"
)
async def delete_page(
    page_id: int,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> Response:
    await services.delete_page.execute(identity, page_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
