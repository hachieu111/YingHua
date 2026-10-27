from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.quiz.application.dto import MistakeReviewView, PracticeResult
from app.modules.quiz.domain.entities import QuestionOrigin

AI_LABEL = "Do AI viết, có thể chưa chính xác"


class PracticeQuestionResponse(BaseModel):
    """Câu luyện KHÔNG kèm đáp án: đáp án chỉ trả sau khi người học chọn."""

    prompt: str
    options: list[str]


class MistakeReviewResponse(BaseModel):
    question_id: int
    term: str
    origin: str = Field(description="llm | fallback")
    explanation: str
    difference: str | None = Field(
        description="Điểm khác giữa đáp án đã chọn và đáp án đúng (chỉ khi do LLM)"
    )
    ai_label: str | None = Field(description="Nhãn nguồn AI; chỉ có khi origin là llm")
    practice: PracticeQuestionResponse | None = Field(
        description="Câu luyện thêm 4 lựa chọn; null nếu không tìm được câu phù hợp"
    )
    cached: bool = Field(description="True nếu lấy từ nội dung đã lưu, không gọi lại LLM")

    @classmethod
    def from_view(cls, view: MistakeReviewView) -> MistakeReviewResponse:
        review = view.review
        practice = review.practice
        return cls(
            question_id=view.question_id,
            term=view.term,
            origin=review.origin.value,
            explanation=review.explanation,
            difference=review.difference,
            ai_label=AI_LABEL if review.origin is QuestionOrigin.LLM else None,
            practice=PracticeQuestionResponse(prompt=practice.prompt, options=list(practice.options))
            if practice
            else None,
            cached=view.cached,
        )


class PracticeAnswerRequest(BaseModel):
    choice: str = Field(min_length=1, max_length=200, description="Một trong các lựa chọn của câu luyện")


class PracticeAnswerResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str

    @classmethod
    def from_result(cls, result: PracticeResult) -> PracticeAnswerResponse:
        return cls(
            is_correct=result.is_correct,
            correct_answer=result.correct_answer,
            explanation=result.explanation,
        )
