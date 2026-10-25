from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.api.public import Identity, get_identity
from app.modules.quiz.api.dependencies import QuizServices, get_quiz_services
from app.modules.quiz.api.schemas import (
    CreateQuizRequest,
    QuizDetailResponse,
    QuizPageResponse,
    QuizSummaryResponse,
    SubmitQuizRequest,
)
from app.modules.quiz.application.dto import AnswerInput, CreateQuizCommand
from app.modules.vocab.api.public import SaveWordResponse

router = APIRouter(prefix="/quizzes", tags=["M09 Kiểm tra"])


@router.get(
    "/summary",
    response_model=QuizSummaryResponse,
    summary="Số từ đủ điều kiện làm bài kiểm tra (F09.01)",
)
async def quiz_summary(
    identity: Identity = Depends(get_identity), services: QuizServices = Depends(get_quiz_services)
) -> QuizSummaryResponse:
    return QuizSummaryResponse.from_summary(await services.summary.execute(identity))


@router.post(
    "",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo bài kiểm tra từ sổ tay; LLM lỗi/tắt thì dùng đề dự phòng (F09.01, F09.08)",
    description=(
        "Dưới số từ tối thiểu → 400 `NOT_ENOUGH_WORDS_FOR_QUIZ` (kèm `details.current`, `details.required`). "
        "Câu hỏi KHÔNG kèm đáp án. `note` có giá trị khi đề được tạo tự động từ từ điển."
    ),
    response_model_exclude_unset=True,  # bài chưa nộp: bỏ hẳn các trường đáp án thay vì trả null
)
async def create_quiz(
    body: CreateQuizRequest,
    identity: Identity = Depends(get_identity),
    services: QuizServices = Depends(get_quiz_services),
) -> QuizDetailResponse:
    detail = await services.create.execute(identity, CreateQuizCommand(body.question_count))
    return QuizDetailResponse.from_detail(detail)


@router.get(
    "",
    response_model=QuizPageResponse,
    summary="Lịch sử bài kiểm tra, mới nhất trước (F09.05)",
)
async def list_quizzes(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    identity: Identity = Depends(get_identity),
    services: QuizServices = Depends(get_quiz_services),
) -> QuizPageResponse:
    result = await services.list_quizzes.execute(identity, page, size)
    return QuizPageResponse.from_page(result, page, size)


@router.get(
    "/{quiz_id}",
    response_model=QuizDetailResponse,
    summary="Mở một bài: đang làm thì không có đáp án, đã nộp thì đầy đủ (F09.02, F09.05)",
    response_model_exclude_unset=True,  # bài chưa nộp: bỏ hẳn các trường đáp án thay vì trả null
)
async def get_quiz(
    quiz_id: int,
    identity: Identity = Depends(get_identity),
    services: QuizServices = Depends(get_quiz_services),
) -> QuizDetailResponse:
    return QuizDetailResponse.from_detail(await services.get.execute(identity, quiz_id))


@router.post(
    "/{quiz_id}/submit",
    response_model=QuizDetailResponse,
    summary="Nộp bài (một lần), chấm điểm và đưa từ sai về ôn sớm (F09.02–F09.04)",
    description=(
        "Nộp lần hai → 409 `QUIZ_ALREADY_SUBMITTED`. Câu không có trong `answers` tính là chưa trả lời."
    ),
    response_model_exclude_unset=True,  # bài chưa nộp: bỏ hẳn các trường đáp án thay vì trả null
)
async def submit_quiz(
    quiz_id: int,
    body: SubmitQuizRequest,
    identity: Identity = Depends(get_identity),
    services: QuizServices = Depends(get_quiz_services),
) -> QuizDetailResponse:
    answers = [AnswerInput(a.question_id, a.answer) for a in body.answers]
    return QuizDetailResponse.from_detail(await services.submit.execute(identity, quiz_id, answers))


@router.post(
    "/{quiz_id}/questions/{question_id}/save-word",
    response_model=SaveWordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lưu từ mở rộng của một câu vào sổ tay sau khi nộp bài (F09.09)",
    description=(
        "Chỉ cho câu từ mở rộng của bài đã nộp (bài chưa nộp → 409 `QUIZ_NOT_SUBMITTED`; câu từ đã lưu → "
        "400 `WORD_NOT_SAVABLE`). Từ mới → 201; từ đã có → 200. Nguồn lưu là `quiz`."
    ),
)
async def save_quiz_word(
    quiz_id: int,
    question_id: int,
    response: Response,
    identity: Identity = Depends(get_identity),
    services: QuizServices = Depends(get_quiz_services),
) -> SaveWordResponse:
    result = await services.save_word.execute(identity, quiz_id, question_id)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SaveWordResponse.from_result(result)
