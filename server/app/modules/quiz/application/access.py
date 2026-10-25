"""Nạp bài kiểm tra có kiểm quyền cho các use case của M09."""

from __future__ import annotations

from app.modules.quiz.application.dto import QuizDetail
from app.modules.quiz.application.ports import QuizUnitOfWork
from app.modules.quiz.domain.entities import Quiz, QuizStatus, TargetKind
from app.modules.quiz.domain.errors import QuizNotFoundError


async def load_quiz(uow: QuizUnitOfWork, owner_id: int, quiz_id: int, *, for_update: bool = False) -> Quiz:
    """Bài của chính chủ sở hữu; bài của người khác được trả lời như không tồn tại (404)."""
    quiz = await (
        uow.quizzes.get_for_update(owner_id, quiz_id) if for_update else uow.quizzes.get(owner_id, quiz_id)
    )
    if quiz is None:
        raise QuizNotFoundError()
    return quiz


async def build_detail(uow: QuizUnitOfWork, quiz: Quiz) -> QuizDetail:
    """Bài kèm câu hỏi và dữ liệu hiển thị. Bài đã nộp kèm các từ đang được ôn lại vì làm sai (F09.04, tải
    lại không tính lại), từ cầu nối của câu từ mở rộng và các câu có thể lưu vào sổ tay (F09.09)."""
    questions = await uow.quizzes.questions(quiz.id)
    example_ids = [q.example_id for q in questions if q.example_id is not None]
    examples = await uow.examples.get_many(example_ids) if example_ids else {}
    if quiz.status is not QuizStatus.SUBMITTED:
        return QuizDetail(quiz, questions, examples=examples)
    wrong_ids = [
        q.vocab_entry_id
        for q in questions
        if q.target_kind is TargetKind.SAVED and q.is_correct is False and q.vocab_entry_id is not None
    ]
    bridge_ids = [q.related_entry_id for q in questions if q.related_entry_id is not None]
    refs = await uow.vocab.entries(quiz.user_id, [*wrong_ids, *bridge_ids])
    terms: list[str] = []
    if quiz.wrong_cards_rescheduled_at is not None:
        terms = list(
            dict.fromkeys(refs[i].term for i in wrong_ids if i in refs and refs[i].status != "ignored")
        )
    related = [q for q in questions if q.target_kind is TargetKind.RELATED]
    saved_terms = await uow.vocab.saved_terms(quiz.user_id, [q.term for q in related])
    return QuizDetail(
        quiz,
        questions,
        terms,
        examples,
        {i: refs[i].term for i in bridge_ids if i in refs},
        {q.id for q in related if q.term not in saved_terms},
    )
