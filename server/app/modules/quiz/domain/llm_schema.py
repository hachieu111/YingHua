"""Kiểm tra lược đồ bộ đề do LLM trả về (F09.07). Không tin dữ liệu của LLM: mọi trường đều được kiểm.

Lược đồ mong đợi (JSON đã phân tích thành dict):
    {"questions": [{"term": str, "type": "multiple_choice" | "fill_blank", "prompt": str,
                    "options": [str, ...] (chỉ trắc nghiệm), "answer": str, "explanation": str | null,
                    "accepted_answers": [str, ...] (tùy chọn, câu điền từ),
                    "example_zh": str | null, "example_vi": str | null (tùy chọn, F09.09)}]}
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.modules.quiz.domain.entities import NewQuestion, QuestionOrigin, QuestionType, QuizWord
from app.modules.quiz.domain.rules import normalize_answer

MAX_PROMPT_CHARS = 500
MAX_ANSWER_CHARS = 200
MAX_EXPLANATION_CHARS = 500
MIN_OPTIONS, MAX_OPTIONS = 2, 6
MAX_ACCEPTED_ANSWERS = 10


@dataclass(frozen=True, slots=True)
class LlmExample:
    """Câu ví dụ do LLM viết; chỉ được dùng sau khi qua kiểm độ khó (F09.09)."""

    zh: str
    vi: str | None


@dataclass(frozen=True, slots=True)
class LlmQuestions:
    """Câu hỏi hợp lệ, tối đa một câu cho mỗi từ, theo thứ tự LLM trả về."""

    questions: list[NewQuestion]
    examples: dict[int, LlmExample] = field(default_factory=dict)  # theo vocab_entry_id


def _text(value: Any, max_chars: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text and len(text) <= max_chars else None


def _options(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not MIN_OPTIONS <= len(value) <= MAX_OPTIONS:
        return None
    options = [_text(v, MAX_ANSWER_CHARS) for v in value]
    if any(o is None for o in options):
        return None
    cleaned = [o for o in options if o is not None]
    if len({normalize_answer(o) for o in cleaned}) != len(cleaned):
        return None
    return cleaned


def _accepted(value: Any) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_ACCEPTED_ANSWERS:
        return None
    accepted = [_text(v, MAX_ANSWER_CHARS) for v in value]
    return None if any(a is None for a in accepted) else [a for a in accepted if a is not None]


def _example(item: dict[str, Any]) -> LlmExample | bool | None:
    """Câu ví dụ của LLM (example_zh, example_vi); False nếu sai kiểu, None nếu không có."""
    values = [item.get("example_zh"), item.get("example_vi")]
    if any(v is not None and not isinstance(v, str) for v in values):
        return False
    zh, vi = (_text(v, MAX_EXPLANATION_CHARS) if v is not None else None for v in values)
    return LlmExample(zh, vi) if zh is not None else None


def _parse_question(
    item: Any, entry_by_term: Mapping[str, int]
) -> tuple[str, NewQuestion, LlmExample | None] | None:
    """(từ, câu hỏi) nếu `item` đúng lược đồ; None nếu sai lược đồ. Từ ngoài danh sách đã chọn cũng trả về
    với khóa rỗng để người gọi phân biệt "sai lược đồ" với "câu lạc đề".
    """
    if not isinstance(item, dict):
        return None
    term = _text(item.get("term"), MAX_ANSWER_CHARS)
    prompt = _text(item.get("prompt"), MAX_PROMPT_CHARS)
    answer = _text(item.get("answer"), MAX_ANSWER_CHARS)
    raw_explanation = item.get("explanation")
    explanation = _text(raw_explanation, MAX_EXPLANATION_CHARS) if raw_explanation is not None else None
    accepted = _accepted(item.get("accepted_answers"))
    example = _example(item)
    if example is False:
        return None
    if term is None or prompt is None or answer is None or accepted is None:
        return None
    if raw_explanation is not None and explanation is None:
        return None
    try:
        qtype = QuestionType(item.get("type"))
    except ValueError:
        return None
    options: list[str] | None = None
    if qtype is QuestionType.MULTIPLE_CHOICE:
        options = _options(item.get("options"))
        if options is None or normalize_answer(answer) not in {normalize_answer(o) for o in options}:
            return None
    elif item.get("options"):
        return None
    question = NewQuestion(
        qtype,
        prompt,
        answer,
        QuestionOrigin.LLM,
        options=options,
        accepted_answers=accepted,
        explanation=explanation,
        vocab_entry_id=entry_by_term.get(term),
        term=term,
    )
    return (
        term if term in entry_by_term else "",
        question,
        example if isinstance(example, LlmExample) else None,
    )


def validate_llm_payload(payload: object, words: Sequence[QuizWord]) -> LlmQuestions | None:
    """Câu hỏi hợp lệ của LLM, hoặc None nếu cả đề sai lược đồ (F09.07 bước 1).

    Sai lược đồ ở bất kỳ câu nào thì cả đề không hợp lệ. Câu về từ không nằm trong danh sách đã chọn bị loại
    (không phải lỗi lược đồ); mỗi từ chỉ giữ câu đầu tiên. Người gọi bù câu dự phòng cho từ thiếu.
    """
    if not isinstance(payload, dict):
        return None
    items = payload.get("questions")
    if not isinstance(items, list) or not items:
        return None
    entry_by_term = {w.term: w.entry_id for w in words}
    kept: dict[str, NewQuestion] = {}
    examples: dict[int, LlmExample] = {}
    for item in items:
        parsed = _parse_question(item, entry_by_term)
        if parsed is None:
            return None
        term, question, example = parsed
        if term and term not in kept:
            kept[term] = question
            if example is not None and question.vocab_entry_id is not None:
                examples[question.vocab_entry_id] = example
    return LlmQuestions(list(kept.values()), examples)
