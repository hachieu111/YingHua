from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.quiz.domain.entities import ExampleRow, MistakeReview, Quiz, QuizQuestion


@dataclass(frozen=True, slots=True)
class QuizSummary:
    eligible_words: int
    min_words: int
    question_count: int
    llm_enabled: bool


@dataclass(frozen=True, slots=True)
class CreateQuizCommand:
    question_count: int | None = None


@dataclass(frozen=True, slots=True)
class AnswerInput:
    question_id: int
    answer: str | None


@dataclass(frozen=True, slots=True)
class QuizDetail:
    """Bài kèm câu hỏi. Bài chưa nộp không được lộ đáp án: tầng api quyết định theo `quiz.status`."""

    quiz: Quiz
    questions: list[QuizQuestion]
    rescheduled_terms: list[str] = field(default_factory=list)
    examples: dict[int, ExampleRow] = field(default_factory=dict)  # theo example_id
    related_terms: dict[int, str] = field(default_factory=dict)  # từ cầu nối: vocab_entry_id -> term
    savable_question_ids: set[int] = field(
        default_factory=set
    )  # câu từ mở rộng, đã nộp, chưa có trong sổ tay


@dataclass(frozen=True, slots=True)
class MistakeReviewView:
    """ "Vì sao sai?" của một câu. Câu luyện chưa kèm đáp án: chỉ trả sau khi người học đã chọn (F09.10)."""

    question_id: int
    term: str
    review: MistakeReview
    cached: bool  # True nếu đã lưu từ trước, không gọi lại LLM


@dataclass(frozen=True, slots=True)
class PracticeResult:
    """Kết quả một lần chọn đáp án câu luyện — chỉ để hiển thị, không lưu, không tính điểm."""

    is_correct: bool
    correct_answer: str
    explanation: str


@dataclass(frozen=True, slots=True)
class QuizPage:
    items: list[Quiz]
    total: int
