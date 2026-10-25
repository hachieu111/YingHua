from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import build_detail, load_quiz
from app.modules.quiz.application.dto import QuizDetail
from app.modules.quiz.application.ports import QuizUnitOfWork


class GetQuizUseCase:
    """F09.02, F09.03, F09.05 — Mở một bài: đang làm chỉ có câu hỏi, đã nộp kèm đáp án (US-NH-46, 47, 49).

    Bài của người khác → 404. Việc ẩn đáp án của bài chưa nộp do tầng api thực hiện theo `quiz.status`;
    dữ liệu trả về luôn đầy đủ để use case nộp bài dùng lại.
    """

    def __init__(self, uow_factory: Callable[[], QuizUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, quiz_id: int, owner_id: int | None = None) -> QuizDetail:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            quiz = await load_quiz(uow, owner, quiz_id)
            return await build_detail(uow, quiz)
