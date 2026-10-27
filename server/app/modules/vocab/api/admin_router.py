"""Quản trị viên xem và sửa sổ tay của người dùng khác (F13.07, US-QT-14). Hợp đồng như `/vocab-entries`."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.vocab.api.dependencies import (
    VocabServices,
    get_export_query,
    get_list_vocab_query,
    get_vocab_services,
)
from app.modules.vocab.api.export_response import export_response
from app.modules.vocab.api.schemas import UpdateVocabRequest, VocabEntryDetailResponse, VocabPageResponse
from app.modules.vocab.application.dto import ListVocabQuery

admin_router = APIRouter(prefix="/admin/users/{user_id}/vocab-entries", tags=["M13 Quản trị"])


@admin_router.get(
    "",
    response_model=VocabPageResponse,
    summary="Quản trị: sổ tay của người dùng, có lọc và phân trang (F13.07)",
)
async def admin_list_vocab(
    user_id: int = Depends(get_target_user_id),
    query: ListVocabQuery = Depends(get_list_vocab_query),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> VocabPageResponse:
    result = await services.list_vocab.execute(admin, query, user_id)
    return VocabPageResponse.from_page(result, query.page, query.size)


@admin_router.get(
    "/export",
    summary="Quản trị: xuất sổ tay của người dùng ra CSV hoặc Anki (F07.08, F13.07)",
)
async def admin_export_vocab(
    format: str = Query(description="csv | anki"),
    user_id: int = Depends(get_target_user_id),
    query: ListVocabQuery = Depends(get_export_query),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    return export_response(await services.export_vocab.execute(admin, format, query, user_id))


@admin_router.get(
    "/{entry_id}",
    response_model=VocabEntryDetailResponse,
    summary="Quản trị: chi tiết một từ của người dùng (F13.07)",
)
async def admin_get_vocab(
    entry_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> VocabEntryDetailResponse:
    return VocabEntryDetailResponse.from_detail(await services.get_vocab.execute(admin, entry_id, user_id))


@admin_router.patch(
    "/{entry_id}",
    response_model=VocabEntryDetailResponse,
    summary="Quản trị: sửa trạng thái, ghi chú, nghĩa, dấu sao của từ; ghi nhật ký (F13.07)",
)
async def admin_update_vocab(
    entry_id: int,
    body: UpdateVocabRequest,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> VocabEntryDetailResponse:
    changes: dict[str, Any] = body.model_dump(exclude_unset=True)
    return VocabEntryDetailResponse.from_detail(
        await services.update_vocab.execute(admin, entry_id, changes, user_id)
    )


@admin_router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quản trị: xóa từ cùng ngữ cảnh, thẻ, lịch sử ôn; ghi nhật ký (F13.07)",
)
async def admin_delete_vocab(
    entry_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    await services.delete_vocab.execute(admin, entry_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.delete(
    "/{entry_id}/contexts/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quản trị: xóa một ngữ cảnh của từ; ghi nhật ký (F13.07)",
)
async def admin_delete_context(
    entry_id: int,
    context_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    await services.delete_context.execute(admin, entry_id, context_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
