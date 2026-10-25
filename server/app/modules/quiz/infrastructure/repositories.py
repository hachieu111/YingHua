from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quiz.domain.entities import (
    ExampleForm,
    FallbackReason,
    GradedAnswer,
    NewQuestion,
    NewQuiz,
    QuestionOrigin,
    QuestionType,
    Quiz,
    QuizQuestion,
    QuizSource,
    QuizStatus,
    TargetKind,
)
from app.modules.quiz.infrastructure.orm_models import QuizModel, QuizQuestionModel


def _quiz(m: QuizModel) -> Quiz:
    return Quiz(
        id=m.id,
        user_id=m.user_id,
        source=QuizSource(m.source),
        status=QuizStatus(m.status),
        question_count=m.question_count,
        created_at=m.created_at,
        note=m.note,
        fallback_reason=FallbackReason(m.fallback_reason) if m.fallback_reason else None,
        score=m.score,
        submitted_at=m.submitted_at,
        wrong_cards_rescheduled_at=m.wrong_cards_rescheduled_at,
        related_score=m.related_score,
        related_count=m.related_count,
    )


def _question(m: QuizQuestionModel) -> QuizQuestion:
    return QuizQuestion(
        id=m.id,
        quiz_id=m.quiz_id,
        position=m.position,
        question_type=QuestionType(m.question_type),
        prompt=m.prompt,
        correct_answer=m.correct_answer,
        origin=QuestionOrigin(m.origin),
        options=list(m.options) if m.options is not None else None,
        accepted_answers=[str(a) for a in (m.accepted_answers or [])],
        explanation=m.explanation,
        vocab_entry_id=m.vocab_entry_id,
        user_answer=m.user_answer,
        is_correct=m.is_correct,
        term=m.term,
        target_kind=TargetKind(m.target_kind),
        related_entry_id=m.related_entry_id,
        example_id=m.example_id,
        example_form=ExampleForm(m.example_form) if m.example_form else None,
        hint=m.hint,
    )


class SqlQuizRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, new_quiz: NewQuiz, questions: Sequence[NewQuestion]
    ) -> tuple[Quiz, list[QuizQuestion]]:
        quiz = QuizModel(
            user_id=new_quiz.user_id,
            source=new_quiz.source.value,
            status=QuizStatus.IN_PROGRESS.value,
            question_count=new_quiz.question_count,
            fallback_reason=new_quiz.fallback_reason.value if new_quiz.fallback_reason else None,
            note=new_quiz.note,
            related_count=new_quiz.related_count,
            created_at=new_quiz.created_at,
        )
        self._session.add(quiz)
        await self._session.flush()
        models = [
            QuizQuestionModel(
                quiz_id=quiz.id,
                position=position,
                question_type=q.question_type.value,
                prompt=q.prompt,
                options=q.options,
                correct_answer=q.correct_answer,
                accepted_answers=q.accepted_answers,
                explanation=q.explanation,
                vocab_entry_id=q.vocab_entry_id,
                origin=q.origin.value,
                term=q.term,
                target_kind=q.target_kind.value,
                related_entry_id=q.related_entry_id,
                example_id=q.example_id,
                example_form=q.example_form.value if q.example_form else None,
                hint=q.hint,
            )
            for position, q in enumerate(questions, start=1)
        ]
        self._session.add_all(models)
        await self._session.flush()
        return _quiz(quiz), [_question(m) for m in models]

    async def get(self, user_id: int, quiz_id: int) -> Quiz | None:
        model = (
            await self._session.execute(
                select(QuizModel).where(QuizModel.id == quiz_id, QuizModel.user_id == user_id)
            )
        ).scalar_one_or_none()
        return _quiz(model) if model else None

    async def get_for_update(self, user_id: int, quiz_id: int) -> Quiz | None:
        model = (
            await self._session.execute(
                select(QuizModel)
                .where(QuizModel.id == quiz_id, QuizModel.user_id == user_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        return _quiz(model) if model else None

    async def questions(self, quiz_id: int) -> list[QuizQuestion]:
        rows = await self._session.execute(
            select(QuizQuestionModel)
            .where(QuizQuestionModel.quiz_id == quiz_id)
            .order_by(QuizQuestionModel.position)
        )
        return [_question(m) for m in rows.scalars()]

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[Quiz], int]:
        total = (
            await self._session.execute(select(func.count(QuizModel.id)).where(QuizModel.user_id == user_id))
        ).scalar_one()
        rows = await self._session.execute(
            select(QuizModel)
            .where(QuizModel.user_id == user_id)
            .order_by(QuizModel.created_at.desc(), QuizModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_quiz(m) for m in rows.scalars()], int(total)

    async def count_llm_between(self, user_id: int, start: datetime, end: datetime) -> int:
        stmt = select(func.count(QuizModel.id)).where(
            QuizModel.user_id == user_id,
            QuizModel.source != QuizSource.FALLBACK.value,
            QuizModel.created_at >= start,
            QuizModel.created_at < end,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def save_result(self, quiz: Quiz, graded: Sequence[GradedAnswer]) -> None:
        await self._session.execute(
            update(QuizModel)
            .where(QuizModel.id == quiz.id, QuizModel.user_id == quiz.user_id)
            .values(
                status=quiz.status.value,
                score=quiz.score,
                related_score=quiz.related_score,
                submitted_at=quiz.submitted_at,
                wrong_cards_rescheduled_at=quiz.wrong_cards_rescheduled_at,
            )
        )
        # Một bài tối đa 20 câu nên cập nhật từng câu cho đơn giản.
        for g in graded:
            await self._session.execute(
                update(QuizQuestionModel)
                .where(QuizQuestionModel.id == g.question_id, QuizQuestionModel.quiz_id == quiz.id)
                .values(user_answer=g.user_answer, is_correct=g.is_correct)
            )

    async def recent_example_ids(self, user_id: int, quizzes: int) -> set[int]:
        latest = (
            select(QuizModel.id)
            .where(QuizModel.user_id == user_id)
            .order_by(QuizModel.created_at.desc(), QuizModel.id.desc())
            .limit(quizzes)
        )
        rows = await self._session.execute(
            select(QuizQuestionModel.example_id).where(
                QuizQuestionModel.quiz_id.in_(latest), QuizQuestionModel.example_id.is_not(None)
            )
        )
        return {example_id for example_id in rows.scalars() if example_id is not None}

    async def delete(self, user_id: int, quiz_id: int) -> None:
        await self._session.execute(
            delete(QuizModel).where(QuizModel.id == quiz_id, QuizModel.user_id == user_id)
        )
