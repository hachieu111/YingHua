from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.modules.quiz.application.dto import QuizDetail, QuizPage, QuizSummary
from app.modules.quiz.domain.entities import Quiz, QuizQuestion, QuizStatus
from app.modules.quiz.domain.rules import MAX_QUESTION_COUNT, MIN_QUESTION_COUNT


class QuizSummaryResponse(BaseModel):
    eligible_words: int = Field(description="Số từ đủ điều kiện ra đề (không tính từ Bỏ qua)")
    min_words: int
    question_count: int = Field(description="Số câu mặc định của một bài")
    llm_enabled: bool

    @classmethod
    def from_summary(cls, s: QuizSummary) -> QuizSummaryResponse:
        return cls(
            eligible_words=s.eligible_words,
            min_words=s.min_words,
            question_count=s.question_count,
            llm_enabled=s.llm_enabled,
        )


class CreateQuizRequest(BaseModel):
    question_count: int | None = Field(
        default=None, ge=MIN_QUESTION_COUNT, le=MAX_QUESTION_COUNT, description="Bỏ trống = số câu mặc định"
    )


class AnswerRequest(BaseModel):
    question_id: int = Field(ge=1)
    answer: str | None = Field(default=None, max_length=200, description="Rỗng/null = chưa trả lời")


class SubmitQuizRequest(BaseModel):
    answers: list[AnswerRequest] = Field(default_factory=list, max_length=MAX_QUESTION_COUNT)


class ExampleResponse(BaseModel):
    """Câu ví dụ. Trước khi nộp chỉ có `zh` và `pinyin` (và chỉ khi câu hỏi không chứa đáp án trong câu)."""

    zh: str
    pinyin: str | None = None
    vi: str | None = None


class RelatedToResponse(BaseModel):
    vocab_entry_id: int
    term: str


class QuizQuestionResponse(BaseModel):
    """Bài chưa nộp chỉ có các trường đầu; sau khi nộp có thêm các trường còn lại (vắng khóa = chưa lộ)."""

    id: int
    position: int
    question_type: str = Field(description="multiple_choice | fill_blank")
    prompt: str
    options: list[str] | None = None
    target_kind: str = Field(description="saved (từ đã lưu) | related (từ mở rộng)")
    hint: str | None = None
    example: ExampleResponse | None = None
    # --- chỉ có sau khi nộp bài ---
    term: str | None = None
    related_to: RelatedToResponse | None = Field(
        default=None, description="Từ đã lưu làm cầu nối của câu từ mở rộng"
    )
    can_save: bool | None = Field(default=None, description="Câu từ mở rộng, từ chưa có trong sổ tay")
    user_answer: str | None = None
    correct_answer: str | None = None
    accepted_answers: list[str] | None = None
    explanation: str | None = None
    is_correct: bool | None = None
    vocab_entry_id: int | None = None
    has_mistake_review: bool | None = Field(
        default=None, description="Câu đã có nội dung 'Vì sao sai?' được lưu (F09.10)"
    )

    @classmethod
    def from_question(cls, q: QuizQuestion, detail: QuizDetail) -> QuizQuestionResponse:
        example = detail.examples.get(q.example_id) if q.example_id is not None else None
        reveal = detail.quiz.status is QuizStatus.SUBMITTED
        common: dict[str, Any] = {
            "id": q.id,
            "position": q.position,
            "question_type": q.question_type.value,
            "prompt": q.prompt,
            "options": q.options,
            "target_kind": q.target_kind.value,
            "hint": q.hint,
        }
        if not reveal:
            # Dạng điền từ chứa đáp án trong câu (và phiên âm) nên không trả câu gốc; dạng chọn bản dịch
            # không trả `vi` vì đó là đáp án.
            safe = example is not None and q.example_form is not None and q.example_form.reveals_sentence
            common["example"] = (
                ExampleResponse(zh=example.zh, pinyin=example.pinyin) if safe and example else None
            )
            return cls(**common)
        related_to = None
        if q.related_entry_id is not None and q.related_entry_id in detail.related_terms:
            related_to = RelatedToResponse(
                vocab_entry_id=q.related_entry_id, term=detail.related_terms[q.related_entry_id]
            )
        common["example"] = (
            ExampleResponse(zh=example.zh, pinyin=example.pinyin, vi=example.vi) if example else None
        )
        return cls(
            **common,
            term=q.term,
            related_to=related_to,
            can_save=q.id in detail.savable_question_ids,
            user_answer=q.user_answer,
            correct_answer=q.correct_answer,
            accepted_answers=q.accepted_answers,
            explanation=q.explanation,
            is_correct=bool(q.is_correct),
            vocab_entry_id=q.vocab_entry_id,
            has_mistake_review=q.mistake_review is not None,
        )


class QuizItemResponse(BaseModel):
    id: int
    status: str
    source: str = Field(description="llm | fallback | mixed")
    score: int | None = Field(description="Số câu đúng trong các câu từ đã lưu")
    question_count: int = Field(description="Số câu từ đã lưu")
    related_score: int | None = Field(description="Số câu đúng trong các câu từ mở rộng (tính riêng)")
    related_count: int = Field(description="Số câu từ mở rộng")
    note: str | None
    created_at: datetime
    submitted_at: datetime | None

    @classmethod
    def from_quiz(cls, q: Quiz) -> QuizItemResponse:
        return cls(
            id=q.id,
            status=q.status.value,
            source=q.source.value,
            score=q.score,
            question_count=q.question_count,
            related_score=q.related_score,
            related_count=q.related_count,
            note=q.note,
            created_at=q.created_at,
            submitted_at=q.submitted_at,
        )


class QuizDetailResponse(QuizItemResponse):
    questions: list[QuizQuestionResponse]
    rescheduled_terms: list[str] = Field(
        default_factory=list, description="Từ làm sai đã được đưa vào ôn lại (chỉ bài đã nộp)"
    )

    @classmethod
    def from_detail(cls, d: QuizDetail) -> QuizDetailResponse:
        item = QuizItemResponse.from_quiz(d.quiz)
        return cls(
            **item.model_dump(),
            questions=[QuizQuestionResponse.from_question(q, d) for q in d.questions],
            rescheduled_terms=d.rescheduled_terms,
        )


class QuizPageResponse(BaseModel):
    items: list[QuizItemResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, p: QuizPage, page: int, size: int) -> QuizPageResponse:
        return cls(
            items=[QuizItemResponse.from_quiz(q) for q in p.items], total=p.total, page=page, size=size
        )
