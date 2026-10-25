"""Câu thoại đã lưu (F07.11, US-NH-70) và lưu tất cả từ của trang (F07.12, US-NH-71)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, get_identity, require_admin
from app.modules.vocab.api.dependencies import VocabServices, get_vocab_services
from app.modules.vocab.api.sentence_schemas import (
    SaveAllWordsResponse,
    SavedSentencePageResponse,
    SavedSentenceResponse,
    SaveSentenceRequest,
    UpdateSentenceNoteRequest,
)
from app.modules.vocab.application.dto import SaveSentenceCommand

TAG = "M07 Sổ tay"
sentences_router = APIRouter(prefix="/saved-sentences", tags=[TAG])
page_words_router = APIRouter(tags=[TAG])
admin_router = APIRouter(prefix="/admin/users/{user_id}/saved-sentences", tags=["M13 Quản trị"])


@sentences_router.post(
    "",
    response_model=SavedSentenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lưu câu thoại (một bong bóng) kèm bản dịch và nguồn (F07.11)",
    description=(
        "Lưu bản sao văn bản của câu. Đã lưu bong bóng này → 409 `SENTENCE_ALREADY_SAVED` "
        "(kèm `details.saved_sentence_id`). Bong bóng không đọc được → 404 `BUBBLE_NOT_FOUND`."
    ),
)
async def save_sentence(
    body: SaveSentenceRequest,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> SavedSentenceResponse:
    item = await services.save_sentence.execute(
        identity, SaveSentenceCommand(body.bubble_id, body.note, body.page_id)
    )
    return SavedSentenceResponse.from_item(item)


@sentences_router.get(
    "",
    response_model=SavedSentencePageResponse,
    summary='Danh sách "Câu thoại đã lưu", mới nhất trước (F07.11)',
)
async def list_sentences(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> SavedSentencePageResponse:
    result = await services.list_sentences.execute(identity, page, size)
    return SavedSentencePageResponse.from_page(result, page, size)


@sentences_router.patch(
    "/{sentence_id}",
    response_model=SavedSentenceResponse,
    summary="Sửa ghi chú của câu thoại đã lưu (F07.11)",
)
async def update_sentence(
    sentence_id: int,
    body: UpdateSentenceNoteRequest,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> SavedSentenceResponse:
    item = await services.update_sentence.execute(identity, sentence_id, body.note)
    return SavedSentenceResponse.from_item(item)


@sentences_router.delete(
    "/{sentence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bỏ lưu câu thoại (F07.11)",
)
async def delete_sentence(
    sentence_id: int,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    await services.delete_sentence.execute(identity, sentence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@page_words_router.post(
    "/pages/{page_id}/save-all-words",
    response_model=SaveAllWordsResponse,
    summary="Lưu tất cả từ chưa có của trang vào sổ tay, tối đa 50 từ mỗi lần (F07.12)",
    description=(
        "Mỗi từ lưu như F07.01 với bong bóng đầu tiên chứa từ, mỗi từ một giao dịch riêng nên lỗi một từ "
        "không hủy các từ khác. Trang chưa xử lý xong hoặc không có từ → 400 `PAGE_HAS_NO_WORDS`. Tất cả "
        "từ đã có → 200 với `saved` rỗng. `remaining` > 0 nghĩa là còn từ chưa lưu, gọi lại để lưu tiếp."
    ),
)
async def save_all_words(
    page_id: int,
    identity: Identity = Depends(get_identity),
    services: VocabServices = Depends(get_vocab_services),
) -> SaveAllWordsResponse:
    return SaveAllWordsResponse.from_result(await services.save_all_words.execute(identity, page_id))


@admin_router.get(
    "",
    response_model=SavedSentencePageResponse,
    summary="Quản trị: câu thoại đã lưu của người dùng (F13.07)",
)
async def admin_list_sentences(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> SavedSentencePageResponse:
    result = await services.list_sentences.execute(admin, page, size, user_id)
    return SavedSentencePageResponse.from_page(result, page, size)


@admin_router.delete(
    "/{sentence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quản trị: xóa câu thoại đã lưu của người dùng; ghi nhật ký (F13.07)",
)
async def admin_delete_sentence(
    sentence_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: VocabServices = Depends(get_vocab_services),
) -> Response:
    await services.delete_sentence.execute(admin, sentence_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
