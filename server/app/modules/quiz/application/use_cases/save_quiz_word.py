from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import load_quiz
from app.modules.quiz.application.ports import QuizUnitOfWork, WordSaver
from app.modules.quiz.domain.entities import QuizStatus, TargetKind
from app.modules.quiz.domain.errors import (
    QuizNotSubmittedError,
    QuizQuestionNotFoundError,
    WordNotSavableError,
)
from app.modules.vocab.application.public import SaveWordCommand, SaveWordResult

QUIZ_ORIGIN = "quiz"


class SaveQuizWordUseCase:
    """F09.09 — Lưu từ mở rộng vào sổ tay sau khi xem kết quả (US-NH-69).

    Chỉ áp dụng cho câu từ mở rộng của bài ĐÃ NỘP; gọi `SaveWordUseCase` (F07.01) với nguồn `quiz`, nên từ
    đã có trong sổ tay được xử lý theo F07.02. Bài của người khác → 404.
    """

    def __init__(self, uow_factory: Callable[[], QuizUnitOfWork], saver: WordSaver) -> None:
        self._uow_factory = uow_factory
        self._saver = saver

    async def execute(self, identity: Identity, quiz_id: int, question_id: int) -> SaveWordResult:
        async with self._uow_factory() as uow:
            quiz = await load_quiz(uow, identity.user_id, quiz_id)
            if quiz.status is not QuizStatus.SUBMITTED:
                raise QuizNotSubmittedError()
            question = next((q for q in await uow.quizzes.questions(quiz.id) if q.id == question_id), None)
            if question is None:
                raise QuizQuestionNotFoundError()
            if question.target_kind is not TargetKind.RELATED:
                raise WordNotSavableError()
            term = question.term
        return await self._saver.execute(identity, SaveWordCommand(term, QUIZ_ORIGIN))
