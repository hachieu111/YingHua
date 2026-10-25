"""Đối chiếu câu hỏi của LLM với dữ liệu từ điển (F09.07 bước 2): loại câu có đáp án mâu thuẫn."""

from __future__ import annotations

import re
from dataclasses import replace

from app.core.glosses import short_meaning
from app.modules.quiz.domain.entities import NewQuestion, QuestionType, QuizWord
from app.modules.quiz.domain.fallback import BLANK, mask_han
from app.modules.quiz.domain.rules import has_han, normalize_answer, option_meaning

MIN_KEYWORD_CHARS = 2
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
# Từ chức năng tiếng Việt không đủ để chứng minh hai nghĩa cùng chỉ một khái niệm.
_STOPWORDS = frozenset(
    {
        "là",
        "của",
        "và",
        "có",
        "một",
        "các",
        "những",
        "được",
        "cho",
        "sự",
        "cái",
        "việc",
        "ở",
        "để",
        "khi",
        "như",
    }
)


def meaning_keywords(text: str | None) -> set[str]:
    """Từ khóa của một nghĩa: các từ tiếng Việt chữ thường, bỏ từ chức năng và từ quá ngắn."""
    words = (w.casefold() for w in _WORD.findall(short_meaning(text)))
    return {w for w in words if len(w) >= MIN_KEYWORD_CHARS and w not in _STOPWORDS}


def contradicts_dictionary(question: NewQuestion, word: QuizWord) -> bool:
    """Đáp án của câu mâu thuẫn với từ điển/nghĩa người học.

    - Đáp án là chữ Hán (điền từ, hoặc chọn từ theo nghĩa): phải đúng bằng từ đang hỏi (hoặc dạng chấp nhận).
    - Đáp án là nghĩa tiếng Việt: phải chia sẻ ít nhất một từ khóa với nghĩa đã biết của từ. Từ chưa có nghĩa
      thì không có gì để đối chiếu nên được chấp nhận.
    """
    answer = question.correct_answer
    if has_han(answer) or question.question_type is QuestionType.FILL_BLANK:
        accepted = {normalize_answer(a) for a in (word.term, *question.accepted_answers)}
        return normalize_answer(answer) not in accepted
    known = meaning_keywords(word.meaning_vi)
    return bool(known) and not known & meaning_keywords(answer)


def example_acceptable(zh: str, term: str, difficulty: int | None, max_level: int) -> bool:
    """Câu ví dụ của LLM dùng được: chứa từ đang hỏi và độ khó (HSK cao nhất trong câu) ≤ `max_level`."""
    return term in zh and difficulty is not None and difficulty <= max_level


MIN_CLEAN_OPTIONS = 3  # sau khi gọn lại, trắc nghiệm nghĩa còn ít hơn số này thì bỏ câu (dùng câu dự phòng)


def clean_meaning_options(question: NewQuestion) -> NewQuestion | None:
    """Gọn phương án/đáp án dạng nghĩa của câu trắc nghiệm LLM: nghĩa ngắn ≤ 60 ký tự, bỏ rỗng/trùng.

    Câu có đáp án là chữ Hán (chọn từ theo nghĩa) giữ nguyên. Trả None khi câu không còn dùng được.
    """
    if question.question_type is not QuestionType.MULTIPLE_CHOICE or has_han(question.correct_answer):
        return question
    answer = option_meaning(question.correct_answer)
    options: list[str] = []
    seen: set[str] = set()
    for raw in question.options or []:
        option = option_meaning(raw)
        key = normalize_answer(option)
        if option and key not in seen:
            seen.add(key)
            options.append(option)
    if not answer or normalize_answer(answer) not in seen or len(options) < MIN_CLEAN_OPTIONS:
        return None
    return replace(question, correct_answer=answer, options=options)


def fill_blank_sentence(question: NewQuestion) -> str | None:
    """Câu điền từ đã điền đáp án vào chỗ trống để kiểm độ khó; None nếu `prompt` không có đúng một ＿＿."""
    if question.question_type is not QuestionType.FILL_BLANK or question.prompt.count(BLANK) != 1:
        return None
    return question.prompt.replace(BLANK, question.correct_answer)


def with_meaning_hint(question: NewQuestion, word: QuizWord) -> NewQuestion:
    """Thêm "(nghĩa: …)" hoặc pinyin vào câu điền từ nếu `prompt` chưa có chữ Việt/Latin nào."""
    if any(c.isalpha() and not has_han(c) for c in question.prompt):
        return question
    meaning = mask_han(option_meaning(word.meaning_vi))  # che chữ Hán để gợi ý không lộ đáp án
    if any(c.isalpha() and not has_han(c) for c in meaning):
        hint = f"(nghĩa: {meaning})"
    elif word.pinyin:
        hint = f"(pinyin: {word.pinyin})"
    else:
        return question
    return replace(question, prompt=f"{question.prompt}\n{hint}")
