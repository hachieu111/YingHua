from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.api.public import Identity, get_identity
from app.modules.library.api.dependencies import LibraryServices, get_library_services
from app.modules.library.api.schemas import (
    ContinueItemResponse,
    FavoriteRequest,
    SeriesPage,
    SeriesResponse,
)
from app.modules.library.domain.entities import LibraryTab

router = APIRouter(tags=["M03 Thư viện"])


@router.get("/library", response_model=SeriesPage, summary="Thư viện cá nhân theo tab (F03.13)")
async def list_library(
    tab: Literal["all", "reading", "favorites", "completed"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesPage:
    result = await services.list_library.execute(identity, LibraryTab(tab), page, size)
    return SeriesPage(
        items=[SeriesResponse.from_view(v) for v in result.items], total=result.total, page=page, size=size
    )


@router.put(
    "/library/{series_id}", response_model=SeriesResponse, summary="Thêm truyện vào Thư viện (F03.13)"
)
async def add_to_library(
    series_id: int,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesResponse:
    return SeriesResponse.from_view(await services.add_to_library.execute(identity, series_id))


@router.delete(
    "/library/{series_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Bỏ truyện khỏi Thư viện (F03.13)"
)
async def remove_from_library(
    series_id: int,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> Response:
    await services.remove_from_library.execute(identity, series_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/library/{series_id}/favorite", response_model=SeriesResponse, summary="Bật/tắt Yêu thích (F03.13)"
)
async def set_favorite(
    series_id: int,
    body: FavoriteRequest,
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> SeriesResponse:
    return SeriesResponse.from_view(
        await services.set_favorite.execute(identity, series_id, body.is_favorite)
    )


@router.get(
    "/reading-progress/continue",
    response_model=list[ContinueItemResponse],
    summary="Truyện đang đọc dở (F03.12)",
)
async def list_continue(
    limit: int = Query(default=10, ge=1, le=50),
    identity: Identity = Depends(get_identity),
    services: LibraryServices = Depends(get_library_services),
) -> list[ContinueItemResponse]:
    return [ContinueItemResponse.from_item(i) for i in await services.list_continue.execute(identity, limit)]
