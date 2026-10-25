from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.auth.api.public import Identity, get_identity
from app.modules.review.api.dependencies import ReviewServices, get_review_services
from app.modules.review.api.schemas import (
    CardStateResponse,
    DueCardsResponse,
    GradeRequest,
    GradeResponse,
    HistoryResponse,
    ReviewSummaryResponse,
)
from app.modules.review.application.dto import GradeCommand

router = APIRouter(tags=["M08 Ôn tập"])

DUE_PAGE_SIZE_DEFAULT = 20
DUE_PAGE_SIZE_MAX = 100


@router.get(
    "/cards/due",
    response_model=DueCardsResponse,
    summary="Thẻ đến hạn của phiên ôn, kèm nội dung hai mặt (F08.01, F08.03, F08.04)",
    description=(
        'Thẻ có `due_at <= bây giờ`, không tạm ngưng, thuộc từ "Đang học"; quá hạn lâu nhất trước. '
        "`deck`: bỏ trống/`all`, `starred` hoặc `series:<id>` (lấy từ GET /vocab-entries/decks)."
    ),
)
async def get_due_cards(
    size: int = Query(default=DUE_PAGE_SIZE_DEFAULT, ge=1, le=DUE_PAGE_SIZE_MAX),
    deck: str | None = Query(default=None, max_length=32),
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> DueCardsResponse:
    return DueCardsResponse.from_batch(await services.get_due.execute(identity, size, deck))


@router.post(
    "/cards/{card_id}/grade",
    response_model=GradeResponse,
    summary="Chấm mức nhớ Quên/Khó/Được/Dễ và lập lịch FSRS (F08.02)",
    description=(
        "Một `presentation_id` chỉ tính một lượt ôn; gửi lại trả kết quả cũ với `duplicate=true`. "
        "Trả lịch mới của thẻ và thẻ kế tiếp (hoặc `session_complete=true`)."
    ),
)
async def grade_card(
    card_id: int,
    body: GradeRequest,
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> GradeResponse:
    command = GradeCommand(card_id, body.rating, body.presentation_id, body.duration_ms, body.deck)
    return GradeResponse.from_result(await services.grade.execute(identity, command))


@router.post(
    "/cards/{card_id}/suspend",
    response_model=CardStateResponse,
    summary="Tạm ngưng thẻ khỏi lịch ôn (F08.05)",
)
async def suspend_card(
    card_id: int,
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> CardStateResponse:
    return CardStateResponse.from_card(await services.suspend.execute(identity, card_id))


@router.post(
    "/cards/{card_id}/resume",
    response_model=CardStateResponse,
    summary="Tiếp tục thẻ đã tạm ngưng (F08.05)",
)
async def resume_card(
    card_id: int,
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> CardStateResponse:
    return CardStateResponse.from_card(await services.resume.execute(identity, card_id))


@router.post(
    "/cards/{card_id}/reset",
    response_model=CardStateResponse,
    summary="Đặt lại thẻ như thẻ mới, giữ lịch sử ôn (F08.05)",
)
async def reset_card(
    card_id: int,
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> CardStateResponse:
    return CardStateResponse.from_card(await services.reset.execute(identity, card_id))


@router.get(
    "/cards/{card_id}/history",
    response_model=HistoryResponse,
    summary="Lịch sử ôn của thẻ, mới nhất trước (F08.06)",
)
async def get_card_history(
    card_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> HistoryResponse:
    return HistoryResponse.from_page(
        await services.history.execute(identity, card_id, page, size), page, size
    )


@router.get(
    "/review/summary",
    response_model=ReviewSummaryResponse,
    summary='Tổng kết ôn tập: màn "hoàn thành" hay "chưa có thẻ" (F08.07)',
)
async def get_review_summary(
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> ReviewSummaryResponse:
    return ReviewSummaryResponse.from_summary(await services.summary.execute(identity))
