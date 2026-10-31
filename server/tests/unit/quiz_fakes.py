"""Bản giả của M09 dùng chung cho test đơn vị (không cần CSDL hay LLM thật)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any

from app.modules.quiz.application.ports import EntryRef, LearnerProfile, QuizGenerationRequest
from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    ExampleRow,
    GradedAnswer,
    MistakeReview,
    NewQuestion,
    NewQuiz,
    QuestionOrigin,
    Quiz,
    QuizQuestion,
    QuizSource,
    QuizStatus,
    QuizWord,
    RelatedCandidate,
    WordContext,
)
from tests.unit.activity_fakes import FakeActivity, FakeLearning
from tests.unit.review_fakes import FakeAudit, FakeCards


class FakeQuizRepo:
    def __init__(self) -> None:
        self.quizzes: dict[int, Quiz] = {}
        self.items: dict[int, list[QuizQuestion]] = {}
        self.deleted: list[int] = []
        self.review_times: dict[int, datetime] = {}

    async def add(
        self, new_quiz: NewQuiz, questions: Sequence[NewQuestion]
    ) -> tuple[Quiz, list[QuizQuestion]]:
        quiz = Quiz(
            id=len(self.quizzes) + 1,
            user_id=new_quiz.user_id,
            source=new_quiz.source,
            status=QuizStatus.IN_PROGRESS,
            question_count=new_quiz.question_count,
            created_at=new_quiz.created_at,
            note=new_quiz.note,
            fallback_reason=new_quiz.fallback_reason,
            related_count=new_quiz.related_count,
        )
        base = sum(len(v) for v in self.items.values())
        rows = [
            QuizQuestion(
                id=base + i,
                quiz_id=quiz.id,
                position=i,
                question_type=q.question_type,
                prompt=q.prompt,
                correct_answer=q.correct_answer,
                origin=q.origin,
                options=q.options,
                accepted_answers=list(q.accepted_answers),
                explanation=q.explanation,
                vocab_entry_id=q.vocab_entry_id,
                term=q.term,
                target_kind=q.target_kind,
                related_entry_id=q.related_entry_id,
                example_id=q.example_id,
                example_form=q.example_form,
                hint=q.hint,
            )
            for i, q in enumerate(questions, start=1)
        ]
        self.quizzes[quiz.id] = quiz
        self.items[quiz.id] = rows
        return quiz, rows

    async def get(self, user_id: int, quiz_id: int) -> Quiz | None:
        quiz = self.quizzes.get(quiz_id)
        return quiz if quiz and quiz.user_id == user_id else None

    async def get_for_update(self, user_id: int, quiz_id: int) -> Quiz | None:
        return await self.get(user_id, quiz_id)

    async def questions(self, quiz_id: int) -> list[QuizQuestion]:
        return list(self.items.get(quiz_id, []))

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[Quiz], int]:
        rows = sorted((q for q in self.quizzes.values() if q.user_id == user_id), key=lambda q: -q.id)
        return rows[offset : offset + limit], len(rows)

    async def count_llm_between(self, user_id: int, start: datetime, end: datetime) -> int:
        return sum(
            1
            for q in self.quizzes.values()
            if q.user_id == user_id and q.source is not QuizSource.FALLBACK and start <= q.created_at < end
        )

    async def save_result(self, quiz: Quiz, graded: Sequence[GradedAnswer]) -> None:
        self.quizzes[quiz.id] = quiz
        by_id = {g.question_id: g for g in graded}
        for q in self.items[quiz.id]:
            if q.id in by_id:
                q.user_answer = by_id[q.id].user_answer
                q.is_correct = by_id[q.id].is_correct

    async def recent_example_ids(self, user_id: int, quizzes: int) -> set[int]:
        latest = sorted((q for q in self.quizzes.values() if q.user_id == user_id), key=lambda q: -q.id)
        return {
            q.example_id for quiz in latest[:quizzes] for q in self.items[quiz.id] if q.example_id is not None
        }

    async def save_mistake_review(
        self, quiz_id: int, question_id: int, review: MistakeReview, at: datetime
    ) -> MistakeReview:
        for q in self.items[quiz_id]:
            if q.id == question_id:
                if q.mistake_review is None:
                    q.mistake_review = review
                    self.review_times[question_id] = at
                return q.mistake_review
        raise KeyError(question_id)

    async def count_llm_mistake_reviews_between(self, user_id: int, start: datetime, end: datetime) -> int:
        return sum(
            1
            for quiz in self.quizzes.values()
            if quiz.user_id == user_id
            for q in self.items[quiz.id]
            if q.mistake_review is not None
            and q.mistake_review.origin is QuestionOrigin.LLM
            and start <= self.review_times[q.id] < end
        )

    async def delete(self, user_id: int, quiz_id: int) -> None:
        self.quizzes.pop(quiz_id, None)
        self.deleted.append(quiz_id)


class FakeQuizVocab:
    def __init__(self, words: list[QuizWord] | None = None) -> None:
        self.words = words or []
        self.ctx: dict[int, list[WordContext]] = {}
        self.status: dict[int, str] = {w.entry_id: w.status for w in self.words}
        self.removed: set[int] = set()
        self.extra_saved: set[str] = set()

    async def quizzable_words(self, user_id: int) -> list[QuizWord]:
        return [
            replace(w, status=self.status[w.entry_id])
            for w in self.words
            if self.status[w.entry_id] != "ignored"
        ]

    async def contexts(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, list[WordContext]]:
        return {i: self.ctx[i] for i in entry_ids if i in self.ctx}

    async def entries(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, EntryRef]:
        terms = {w.entry_id: w.term for w in self.words}
        return {
            i: EntryRef(i, terms[i], self.status[i])
            for i in entry_ids
            if i in terms and i not in self.removed
        }

    async def saved_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        return {
            w.term for w in self.words if w.term in terms and w.entry_id not in self.removed
        } | self.extra_saved

    async def mark_learning(self, user_id: int, entry_ids: Sequence[int], now: datetime) -> None:
        for i in entry_ids:
            if self.status.get(i) == "known":
                self.status[i] = "learning"


class FakeExamples:
    """Câu ví dụ giả theo từ; `translations` là kho bản dịch nhiễu."""

    def __init__(
        self, by_term: dict[str, list[ExampleRow]] | None = None, translations: list[str] | None = None
    ) -> None:
        self.by_term = by_term or {}
        self.translations = translations or []
        self.find_calls: list[tuple[str, int]] = []

    async def find(self, term: str, max_difficulty: int, limit: int) -> list[ExampleRow]:
        self.find_calls.append((term, max_difficulty))
        rows = self.by_term.get(term, [])
        return [e for e in rows if e.difficulty_level is not None and e.difficulty_level <= max_difficulty][
            :limit
        ]

    async def get_many(self, example_ids: Sequence[int]) -> dict[int, ExampleRow]:
        return {e.id: e for rows in self.by_term.values() for e in rows if e.id in example_ids}

    async def sample_translations(self, difficulty: int, exclude_ids: Sequence[int], limit: int) -> list[str]:
        return self.translations[:limit]


class FakeRelated:
    def __init__(self, candidates: list[RelatedCandidate] | None = None) -> None:
        self.items = candidates or []
        self.calls = 0

    async def candidates(
        self, user_id: int, saved: Sequence[QuizWord], learner_level: int | None
    ) -> list[RelatedCandidate]:
        self.calls += 1
        return list(self.items)


class FakeQuizUow:
    def __init__(
        self,
        vocab: FakeQuizVocab,
        repo: FakeQuizRepo | None = None,
        cards: FakeCards | None = None,
        examples: FakeExamples | None = None,
    ) -> None:
        self.examples = examples or FakeExamples()
        self.quizzes = repo or FakeQuizRepo()
        self.vocab = vocab
        self.cards = cards or FakeCards()
        self.audit = FakeAudit()
        self.activity = FakeActivity()
        self.learning = FakeLearning()
        self.commits = 0

    async def __aenter__(self) -> FakeQuizUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakeProfiles:
    def __init__(self, hsk_level: int | None = 2, timezone: str | None = "UTC") -> None:
        self.profile = LearnerProfile(hsk_level, timezone)

    async def profile_of(self, user_id: int) -> LearnerProfile:
        return self.profile


class FakeDistractors:
    """Mỗi cấp có sẵn 8 từ HSK giả."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    async def sample(self, level: int, limit: int, exclude: Sequence[str]) -> list[DistractorCandidate]:
        self.calls.append(level)
        return [DistractorCandidate(f"HSK{level}词{i}", f"nghĩa cấp {level} số {i}") for i in range(8)]


class FakeGenerator:
    """Trả lần lượt các kết quả đã định sẵn; Exception thì ném ra, giá trị khác thì trả về."""

    def __init__(self, *results: object, delay: float = 0.0) -> None:
        self.results = list(results)
        self.requests: list[QuizGenerationRequest] = []
        self.delay = delay

    async def generate(self, request: QuizGenerationRequest) -> object:
        self.requests.append(request)
        if self.delay:
            await asyncio.sleep(self.delay)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
