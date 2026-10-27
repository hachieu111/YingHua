"""Giải thích lỗi sai và câu luyện thêm (F09.10, US-NH-79): kiểm tra thuần nội dung do LLM trả về và quy tắc
chấm câu luyện.

Lược đồ LLM mong đợi (JSON đã phân tích thành dict):
    {"explanation": str, "difference": str,
     "practice": {"prompt": str, "options": [4 str], "answer": str, "explanation": str}}
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from app.modules.quiz.domain.entities import (
    MistakeReview,
    NewQuestion,
    PracticeQuestion,
    QuestionOrigin,
    QuestionType,
)
from app.modules.quiz.domain.rules import OPTION_COUNT, normalize_answer

MAX_TEXT_CHARS = 500
MAX_OPTION_CHARS = 200
MAX_CHOSEN_CHARS = 60  # đáp án người học gõ/chọn gửi cho LLM bị cắt ngắn
_HAN_RUN = re.compile(r"[㐀-䶿一-鿿\U00020000-\U0002fa1f]+")


def _text(value: Any, max_chars: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text and len(text) <= max_chars else None


def han_runs(text: str) -> list[str]:
    return _HAN_RUN.findall(text)


def chosen_for_llm(user_answer: str | None) -> str | None:
    """Đáp án người học đã chọn, gọn một dòng, để gửi LLM; None nếu bỏ trống."""
    if user_answer is None or not user_answer.strip():
        return None
    return " ".join(user_answer.split())[:MAX_CHOSEN_CHARS]


def _parse_practice(raw: Any) -> PracticeQuestion | None:
    if not isinstance(raw, dict):
        return None
    prompt = _text(raw.get("prompt"), MAX_TEXT_CHARS)
    answer = _text(raw.get("answer"), MAX_OPTION_CHARS)
    explanation = _text(raw.get("explanation"), MAX_TEXT_CHARS)
    raw_options = raw.get("options")
    if prompt is None or answer is None or explanation is None or not isinstance(raw_options, list):
        return None
    if len(raw_options) != OPTION_COUNT:
        return None
    options = [_text(o, MAX_OPTION_CHARS) for o in raw_options]
    if any(o is None for o in options):
        return None
    cleaned = [o for o in options if o is not None]
    if len({normalize_answer(o) for o in cleaned}) != OPTION_COUNT:
        return None
    matches = [o for o in cleaned if normalize_answer(o) == normalize_answer(answer)]
    if len(matches) != 1:  # đáp án phải nằm trong 4 lựa chọn và không trùng lựa chọn khác
        return None
    return PracticeQuestion(prompt, tuple(cleaned), matches[0], explanation)


def parse_llm_review(payload: object) -> MistakeReview | None:
    """Nội dung đúng lược đồ, hoặc None nếu sai bất kỳ chỗ nào (F09.10 bước 5, tiêu chí 5)."""
    if not isinstance(payload, dict):
        return None
    explanation = _text(payload.get("explanation"), MAX_TEXT_CHARS)
    difference = _text(payload.get("difference"), MAX_TEXT_CHARS)
    practice = _parse_practice(payload.get("practice"))
    if explanation is None or difference is None or practice is None:
        return None
    return MistakeReview(explanation, QuestionOrigin.LLM, difference, practice)


def practice_mentions_term(practice: PracticeQuestion, term: str) -> bool:
    """Câu luyện phải chứa từ cần học: trong câu hỏi, đáp án hoặc một lựa chọn."""
    return term in practice.prompt or any(term in option for option in practice.options)


def practice_as_question(practice: PracticeQuestion, term: str) -> NewQuestion:
    """Dạng `NewQuestion` để dùng lại các phép kiểm đối chiếu từ điển của F09.07."""
    return NewQuestion(
        QuestionType.MULTIPLE_CHOICE,
        practice.prompt,
        practice.answer,
        QuestionOrigin.LLM,
        options=list(practice.options),
        explanation=practice.explanation,
        term=term,
    )


def with_cleaned_options(practice: PracticeQuestion, cleaned: NewQuestion) -> PracticeQuestion | None:
    """Câu luyện sau khi gọn nghĩa; None nếu còn chưa đủ 4 lựa chọn khác nhau."""
    options = tuple(cleaned.options or ())
    if len(options) != OPTION_COUNT:
        return None
    return replace(practice, options=options, answer=cleaned.correct_answer)


def is_correct_choice(practice: PracticeQuestion, choice: str) -> bool:
    return normalize_answer(choice) == normalize_answer(practice.answer)


def is_listed_choice(practice: PracticeQuestion, choice: str) -> bool:
    return normalize_answer(choice) in {normalize_answer(o) for o in practice.options}


def practice_from_question(question: NewQuestion) -> PracticeQuestion | None:
    """Câu luyện dự phòng dựng từ một câu hỏi trắc nghiệm của từ điển/Tatoeba (đủ 4 lựa chọn)."""
    options = tuple(question.options or ())
    if question.question_type is not QuestionType.MULTIPLE_CHOICE or len(options) != OPTION_COUNT:
        return None
    return PracticeQuestion(
        question.prompt, options, question.correct_answer, (question.explanation or "").strip()
    )


def review_to_json(review: MistakeReview) -> dict[str, Any]:
    practice = review.practice
    return {
        "origin": review.origin.value,
        "explanation": review.explanation,
        "difference": review.difference,
        "practice": None
        if practice is None
        else {
            "prompt": practice.prompt,
            "options": list(practice.options),
            "answer": practice.answer,
            "explanation": practice.explanation,
        },
    }


def review_from_json(data: object) -> MistakeReview | None:
    """Đọc lại nội dung đã lưu; dữ liệu hỏng trả None (coi như chưa có)."""
    if not isinstance(data, dict):
        return None
    try:
        raw = data.get("practice")
        practice = (
            None
            if raw is None
            else PracticeQuestion(raw["prompt"], tuple(raw["options"]), raw["answer"], raw["explanation"])
        )
        return MistakeReview(
            data["explanation"], QuestionOrigin(data["origin"]), data.get("difference"), practice
        )
    except (KeyError, TypeError, ValueError):
        return None
