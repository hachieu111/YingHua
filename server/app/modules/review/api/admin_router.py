"""Quản trị viên xem tổng quan, thẻ và lịch sử ôn của người dùng khác (F13.07, US-QT-14).

Đặt ở M08 (không ở M13) để tránh vòng phụ thuộc: M03/M07/M08 đã phụ thuộc M13 (nhật ký quản trị), nên M13
không được import ngược các module đó. Tổng quan cần dữ liệu của cả ba module nên đặt ở module đứng trên cùng.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.review.api.admin_schemas import AdminCardPageResponse, UserOverviewResponse
from app.modules.review.api.dependencies import ReviewServices, get_review_services
from app.modules.review.api.schemas import CardStateResponse, HistoryResponse, ReviewSummaryResponse
from app.modules.review.application.dto import ListCardsQuery

admin_router = APIRouter(prefix="/admin/users/{user_id}", tags=["M13 Quản trị"])


@admin_router.get(
    "/overview",
    response_model=UserOverviewResponse,
    summary="Quản trị: tổng quan hồ sơ và số liệu học tập của người dùng (F13.07)",
)
async def admin_user_overview(
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> UserOverviewResponse:
    return UserOverviewResponse.from_overview(await services.overview.execute(admin, user_id))


@admin_router.get(
    "/review/summary",
    response_model=ReviewSummaryResponse,
    summary="Quản trị: tổng kết ôn tập của người dùng (F13.07)",
)
async def admin_review_summary(
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> ReviewSummaryResponse:
    return ReviewSummaryResponse.from_summary(await services.summary.execute(admin, user_id))


@admin_router.get(
    "/cards",
    response_model=AdminCardPageResponse,
    summary="Quản trị: danh sách thẻ của người dùng kèm từ (F13.07)",
)
async def admin_list_cards(
    state: str | None = Query(default=None, max_length=12, description="learning | review | relearning"),
    suspended: bool | None = Query(default=None, description="true: chỉ thẻ đang tạm ngưng"),
    due: bool | None = Query(default=None, description="true: chỉ thẻ đến hạn; false: thẻ chưa đến hạn"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> AdminCardPageResponse:
    query = ListCardsQuery(state, suspended, due, page, size)
    return AdminCardPageResponse.from_page(
        await services.list_cards.execute(admin, query, user_id), page, size
    )


@admin_router.get(
    "/cards/{card_id}/history",
    response_model=HistoryResponse,
    summary="Quản trị: lịch sử ôn của một thẻ (F13.07)",
)
async def admin_card_history(
    card_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> HistoryResponse:
    result = await services.history.execute(admin, card_id, page, size, user_id)
    return HistoryResponse.from_page(result, page, size)


@admin_router.post(
    "/cards/{card_id}/suspend",
    response_model=CardStateResponse,
    summary="Quản trị: tạm ngưng thẻ của người dùng; ghi nhật ký (F13.07)",
)
async def admin_suspend_card(
    card_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> CardStateResponse:
    return CardStateResponse.from_card(await services.suspend.execute(admin, card_id, user_id))


@admin_router.post(
    "/cards/{card_id}/resume",
    response_model=CardStateResponse,
    summary="Quản trị: tiếp tục thẻ của người dùng; ghi nhật ký (F13.07)",
)
async def admin_resume_card(
    card_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> CardStateResponse:
    return CardStateResponse.from_card(await services.resume.execute(admin, card_id, user_id))


@admin_router.post(
    "/cards/{card_id}/reset",
    response_model=CardStateResponse,
    summary="Quản trị: đặt lại thẻ của người dùng như thẻ mới; ghi nhật ký (F13.07)",
)
async def admin_reset_card(
    card_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: ReviewServices = Depends(get_review_services),
) -> CardStateResponse:
    return CardStateResponse.from_card(await services.reset.execute(admin, card_id, user_id))
