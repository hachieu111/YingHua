from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.core.uploads import read_image_upload
from app.modules.auth.api.public import Identity, get_identity, get_optional_identity
from app.modules.library.api.dependencies import LibraryServices, get_library_services
from app.modules.library.api.schemas import (
    ChapterResponse,
    CreateChapterRequest,
    CreateSeriesRequest,
    RatingRequest,
    RatingResponse,
    SeriesDetailResponse,
    SeriesPage,
    SeriesResponse,
    UpdateSeriesRequest,
)
from app.modules.library.application.dto import ChapterInput, SeriesInput

router = APIRouter(prefix="/series", tags=["M03 Thư viện"])


@router.get("", response_model=SeriesPage, summary="Duyệt và tìm truyện (F03.02)")
async def list_series(
    scope: str = Query(
        default="public", description="`public` (thư viện chung) hoặc `mine` (truyện của tôi)"
    ),
    q: str | None = Query(default=None, max_length=100, description="Tên truyện chứa từ khóa"),
    hsk: int | None = Query(default=None, ge=1, le=9, description="Cấp HSK ước lượng"),
    genre: str | None = Query(default=None, max_length=32),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity | None = Depends(get_optional_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesPage:
    result = await services.list_series.execute(identity, scope, q, hsk, genre, page, size)
    return SeriesPage(
        items=[SeriesResponse.from_view(v) for v in result.items], total=result.total, page=page, size=size
    )


@router.post(
    "",
    response_model=SeriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo truyện (F03.04, F03.05)",
)
async def create_series(
    body: CreateSeriesRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesResponse:
    data = SeriesInput(**{**body.model_dump(), "genres": tuple(body.genres)})
    return SeriesResponse.from_view(await services.create_series.execute(identity, data))


@router.get("/{series_id}", response_model=SeriesDetailResponse, summary="Chi tiết truyện (F03.02, F03.03)")
async def get_series(
    series_id: int,
    identity: Identity | None = Depends(get_optional_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesDetailResponse:
    return SeriesDetailResponse.from_detail(await services.get_series.execute(identity, series_id))


@router.patch("/{series_id}", response_model=SeriesResponse, summary="Sửa truyện (F03.09, F03.05, F03.11)")
async def update_series(
    series_id: int,
    body: UpdateSeriesRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesResponse:
    changes = body.model_dump(exclude_unset=True)
    return SeriesResponse.from_view(await services.update_series.execute(identity, series_id, changes))


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa truyện (F03.09, F03.11)")
async def delete_series(
    series_id: int,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> Response:
    await services.delete_series.execute(identity, series_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{series_id}/cover", response_model=SeriesResponse, summary="Đặt ảnh bìa truyện (F03.04)")
async def set_cover(
    series_id: int,
    file: UploadFile = File(description="Ảnh bìa jpg/png/webp"),
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesResponse:
    upload = await read_image_upload(file, services.max_upload_bytes)
    return SeriesResponse.from_view(await services.set_cover.execute(identity, series_id, upload))


@router.post(
    "/{series_id}/chapters",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm chương (F03.06)",
)
async def create_chapter(
    series_id: int,
    body: CreateChapterRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> ChapterResponse:
    data = ChapterInput(number=body.number, title=body.title, is_trial=body.is_trial)
    return ChapterResponse.from_chapter(await services.create_chapter.execute(identity, series_id, data))


@router.put("/{series_id}/rating", response_model=RatingResponse, summary="Chấm sao truyện (F03.14)")
async def rate_series(
    series_id: int,
    body: RatingRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> RatingResponse:
    return RatingResponse.from_result(await services.rate_series.execute(identity, series_id, body.stars))
