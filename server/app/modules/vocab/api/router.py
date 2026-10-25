from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.modules.auth.api.public import Identity, get_identity
from app.modules.vocab.api.dependencies import VocabServices, get_list_vocab_query, get_vocab_services
from app.modules.vocab.api.schemas import (
    DeckListResponse,
    SaveWordRequest,
    SaveWordResponse,
    UpdateVocabRequest,
    VocabEntryDetailResponse,
    VocabPageResponse,
)
from app.modules.vocab.application.dto import ListVocabQuery, SaveWordCommand

router = APIRouter(prefix="/vocab-entries", tags=["M07 Sổ tay"])


@router.post(
    "",
    response_model=SaveWordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lưu từ vào sổ tay kèm ngữ cảnh và 3 thẻ ôn (F07.01, F07.02)",
    description=(
        "Từ mới → 201, tạo mục từ + ngữ cảnh + 3 thẻ trong một giao dịch. Từ đã có → 200, chỉ thêm ngữ cảnh "
        "nếu bong bóng chưa có (không tạo thẻ, không đổi lịch ôn). Đã có đúng ngữ cảnh đó → 409 "
        "`VOCAB_CONTEXT_ALREADY_SAVED` (kèm `details.vocab_entry_id`). `snippet_missing=true` nghĩa là không "
        "cắt được ảnh bong bóng nhưng đã lưu câu văn."
    ),
)
async def save_word(
    body: SaveWordRequest,
    response: Response,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> SaveWordResponse:
    result = await services.save_word.execute(
        identity,
        SaveWordCommand(body.term, body.source, body.bubble_id, body.page_id, body.meaning_vi),
    )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SaveWordResponse.from_result(result)


@router.get(
    "",
    response_model=VocabPageResponse,
    summary="Xem và lọc sổ tay theo HSK, trạng thái, từ khóa, dấu sao, truyện (F07.07)",
)
async def list_vocab(
    query: ListVocabQuery = Depends(get_list_vocab_query),
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> VocabPageResponse:
    result = await services.list_vocab.execute(identity, query)
    return VocabPageResponse.from_page(result, query.page, query.size)


@router.get(
    "/decks",
    response_model=DeckListResponse,
    summary='Bộ thẻ theo truyện và bộ "Từ đánh dấu sao" cho màn Flashcard (F07.07, F08.01)',
)
async def list_decks(
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> DeckListResponse:
    return DeckListResponse.from_list(await services.list_decks.execute(identity))


@router.get(
    "/{entry_id}",
    response_model=VocabEntryDetailResponse,
    summary="Chi tiết một từ: ngữ cảnh, nguồn truyện, ba thẻ (F07.05, F07.07)",
)
async def get_vocab(
    entry_id: int,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> VocabEntryDetailResponse:
    return VocabEntryDetailResponse.from_detail(await services.get_vocab.execute(identity, entry_id))


@router.patch(
    "/{entry_id}",
    response_model=VocabEntryDetailResponse,
    summary="Đổi trạng thái học, ghi chú, nghĩa, dấu sao (F07.03, F07.04)",
)
async def update_vocab(
    entry_id: int,
    body: UpdateVocabRequest,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> VocabEntryDetailResponse:
    changes: dict[str, Any] = body.model_dump(exclude_unset=True)
    return VocabEntryDetailResponse.from_detail(
        await services.update_vocab.execute(identity, entry_id, changes)
    )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa từ cùng ngữ cảnh, thẻ và lịch sử ôn (F07.06)",
)
async def delete_vocab(
    entry_id: int,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    await services.delete_vocab.execute(identity, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{entry_id}/contexts/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa một ngữ cảnh của từ; từ và thẻ giữ nguyên (F07.05)",
)
async def delete_context(
    entry_id: int,
    context_id: int,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    await services.delete_context.execute(identity, entry_id, context_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
