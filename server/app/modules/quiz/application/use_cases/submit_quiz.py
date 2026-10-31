from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from app.core.clock import Clock
from app.core.learning_events import LearningEvent, LearningSource
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import build_detail, load_quiz
from app.modules.quiz.application.dto import AnswerInput, QuizDetail
from app.modules.quiz.application.ports import QuizUnitOfWork
from app.modules.quiz.domain.entities import GradedAnswer, QuizQuestion, QuizStatus, TargetKind
from app.modules.quiz.domain.errors import InvalidQuizAnswersError, QuizAlreadySubmittedError
from app.modules.quiz.domain.rules import is_correct_answer
from app.modules.review.application.public import RescheduleCardsNowUseCase
from app.modules.stats.application.public import ActivityDelta

STATUS_IGNORED = "ignored"
STATUS_KNOWN = "known"


class SubmitQuizUseCase:
    """F09.02–F09.04, F09.09 — Nộp bài, chấm ở máy chủ và đưa từ sai về ôn sớm (US-NH-46, 47, 48, 69).

    Điểm của câu từ đã lưu (`score`) và của câu từ mở rộng (`related_score`) tính RIÊNG; ôn sớm chỉ áp dụng
    cho câu từ đã lưu, câu từ mở rộng đúng hay sai đều không đụng tới lịch FSRS.

    Mỗi bài nộp đúng một lần (nộp lại → 409). Câu chưa trả lời tính là sai; điểm là số câu đúng. Trong CÙNG
    giao dịch: lưu điểm và đáp án, với từ sai đặt `due = now` cho mọi thẻ (giữ S, D, không ghi lượt ôn FSRS),
    bỏ tạm ngưng, chuyển "Đã thuộc" về "Đang học", rồi đánh dấu `wrong_cards_rescheduled_at`. Từ "Bỏ qua" và
    từ đã bị xóa khỏi sổ tay sau khi ra đề được bỏ qua. Bài của người khác → 404.
    Cộng `quizzes_done` của ngày rồi ghi XP (F16.02) trong cùng giao dịch (F12.01).
    """

    def __init__(
        self,
        uow_factory: Callable[[], QuizUnitOfWork],
        reschedule: RescheduleCardsNowUseCase,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._reschedule = reschedule
        self._clock = clock

    async def execute(self, identity: Identity, quiz_id: int, answers: Sequence[AnswerInput]) -> QuizDetail:
        user_id = identity.user_id
        now = self._clock.now()
        async with self._uow_factory() as uow:
            quiz = await load_quiz(uow, user_id, quiz_id, for_update=True)
            if quiz.status is QuizStatus.SUBMITTED:
                raise QuizAlreadySubmittedError()
            questions = await uow.quizzes.questions(quiz.id)
            graded = _grade(questions, answers)
            quiz.status = QuizStatus.SUBMITTED
            quiz.submitted_at = now
            saved = [
                (q, g) for q, g in zip(questions, graded, strict=True) if q.target_kind is TargetKind.SAVED
            ]
            related = [
                g for q, g in zip(questions, graded, strict=True) if q.target_kind is TargetKind.RELATED
            ]
            quiz.score = sum(1 for _, g in saved if g.is_correct)
            quiz.related_score = sum(1 for g in related if g.is_correct) if related else None
            wrong_entries = [
                q.vocab_entry_id for q, g in saved if not g.is_correct and q.vocab_entry_id is not None
            ]
            await self._reschedule_wrong(uow, user_id, list(dict.fromkeys(wrong_entries)), now)
            quiz.wrong_cards_rescheduled_at = now
            await uow.quizzes.save_result(quiz, graded)
            await uow.activity.record(user_id, now, ActivityDelta(quizzes_done=1))
            await uow.learning.record(_learning_event(user_id, quiz.id, now, graded))
            await uow.commit()
            await uow.learning.after_commit()
            return await build_detail(uow, quiz)

    async def _reschedule_wrong(
        self, uow: QuizUnitOfWork, user_id: int, entry_ids: list[int], now: datetime
    ) -> None:
        refs = await uow.vocab.entries(user_id, entry_ids)
        active = [i for i in entry_ids if i in refs and refs[i].status != STATUS_IGNORED]
        await self._reschedule.execute(uow.cards, user_id, active, now)
        await uow.vocab.mark_learning(user_id, [i for i in active if refs[i].status == STATUS_KNOWN], now)


def _learning_event(
    user_id: int, quiz_id: int, now: datetime, graded: Sequence[GradedAnswer]
) -> LearningEvent:
    """Sự kiện XP của bài (F16.02): số câu đúng, số câu đã trả lời và tổng số câu (M16 tự quyết định điểm)."""
    answered = sum(1 for g in graded if g.user_answer)
    correct = sum(1 for g in graded if g.is_correct)
    return LearningEvent(
        user_id, LearningSource.QUIZ, str(quiz_id), now, value=correct, answered=answered, total=len(graded)
    )


def _grade(questions: Sequence[QuizQuestion], answers: Sequence[AnswerInput]) -> list[GradedAnswer]:
    """Chấm từng câu theo thứ tự câu. Đáp án trỏ tới câu không thuộc bài hoặc gửi trùng một câu là lỗi."""
    valid_ids = {q.id for q in questions}
    given: dict[int, str | None] = {}
    for a in answers:
        if a.question_id not in valid_ids or a.question_id in given:
            raise InvalidQuizAnswersError()
        given[a.question_id] = a.answer.strip() if a.answer is not None else None
    return [
        GradedAnswer(
            q.id,
            given.get(q.id),
            is_correct_answer(q.question_type, given.get(q.id), q.correct_answer, q.accepted_answers),
        )
        for q in questions
    ]
