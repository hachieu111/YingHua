"""Quản trị viên xem và xóa bài kiểm tra của người dùng khác (F13.07, US-QT-14). Hợp đồng như `/quizzes`."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.admin.api.public import get_target_user_id
from app.modules.auth.api.public import Identity, require_admin
from app.modules.quiz.api.dependencies import QuizServices, get_quiz_services
from app.modules.quiz.api.schemas import QuizDetailResponse, QuizPageResponse

admin_router = APIRouter(prefix="/admin/users/{user_id}/quizzes", tags=["M13 Quản trị"])


@admin_router.get(
    "",
    response_model=QuizPageResponse,
    summary="Quản trị: lịch sử bài kiểm tra của người dùng (F13.07)",
)
async def admin_list_quizzes(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: QuizServices = Depends(get_quiz_services),
) -> QuizPageResponse:
    result = await services.list_quizzes.execute(admin, page, size, user_id)
    return QuizPageResponse.from_page(result, page, size)


@admin_router.get(
    "/{quiz_id}",
    response_model=QuizDetailResponse,
    summary="Quản trị: chi tiết một bài kiểm tra của người dùng (F13.07)",
    response_model_exclude_unset=True,
)
async def admin_get_quiz(
    quiz_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: QuizServices = Depends(get_quiz_services),
) -> QuizDetailResponse:
    return QuizDetailResponse.from_detail(await services.get.execute(admin, quiz_id, user_id))


@admin_router.delete(
    "/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quản trị: xóa bài kiểm tra của người dùng; ghi nhật ký (F13.07)",
)
async def admin_delete_quiz(
    quiz_id: int,
    user_id: int = Depends(get_target_user_id),
    admin: Identity = Depends(require_admin),
    services: QuizServices = Depends(get_quiz_services),
) -> Response:
    await services.delete.execute(admin, quiz_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
