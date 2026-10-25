from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.modules.auth.api.public import Identity, get_optional_identity
from app.modules.library.api.dependencies import LibraryServices, get_library_services

router = APIRouter(prefix="/files", tags=["M03 Thư viện"])


@router.get(
    "/{file_id}",
    summary="Tải một tệp ảnh có kiểm quyền (F03.10, F03.03, F01.10)",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}, "description": "Nội dung ảnh"}},
)
async def get_file(
    file_id: int,
    identity: Identity | None = Depends(get_optional_identity),
    services: LibraryServices = Depends(get_library_services),
) -> Response:
    content = await services.get_file.execute(identity, file_id)
    return Response(
        content=content.data,
        media_type=content.mime_type,
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )
