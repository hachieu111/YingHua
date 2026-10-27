from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import load_wrong_question
from app.modules.quiz.application.dto import PracticeResult
from app.modules.quiz.application.ports import QuizUnitOfWork
from app.modules.quiz.domain.errors import InvalidPracticeChoiceError, MistakePracticeNotFoundError
from app.modules.quiz.domain.mistake_review import is_correct_choice, is_listed_choice


class AnswerMistakePracticeUseCase:
    """F09.10 bước 8 — Chấm câu luyện thêm của "Vì sao sai?" ở máy chủ (US-NH-79).

    Chỉ trả đáp án đúng SAU khi người học đã chọn. Kết quả KHÔNG được lưu: không đổi điểm bài, không ghi lượt
    ôn, không đụng thẻ FSRS (F08.02, F09.04), nên không có giao dịch ghi. Câu chưa có "Vì sao sai?" hoặc không
    có câu luyện → 404; lựa chọn ngoài 4 phương án → 400.
    """

    def __init__(self, uow_factory: Callable[[], QuizUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, quiz_id: int, question_id: int, choice: str
    ) -> PracticeResult:
        async with self._uow_factory() as uow:
            question = await load_wrong_question(uow, identity.user_id, quiz_id, question_id)
        review = question.mistake_review
        practice = review.practice if review is not None else None
        if practice is None:
            raise MistakePracticeNotFoundError()
        if not is_listed_choice(practice, choice):
            raise InvalidPracticeChoiceError()
        return PracticeResult(is_correct_choice(practice, choice), practice.answer, practice.explanation)
