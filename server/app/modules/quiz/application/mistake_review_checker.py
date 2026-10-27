"""Kiểm "Vì sao sai?" do LLM sinh trước khi lưu (F09.10 bước 5), cùng cách kiểm với F09.07."""

from __future__ import annotations

import logging

from app.modules.quiz.application.ports import ExampleLevelChecker
from app.modules.quiz.domain.entities import MistakeReview, QuizWord
from app.modules.quiz.domain.examples import example_difficulty_cap
from app.modules.quiz.domain.llm_review import clean_meaning_options, contradicts_dictionary
from app.modules.quiz.domain.mistake_review import (
    han_runs,
    parse_llm_review,
    practice_as_question,
    practice_mentions_term,
    with_cleaned_options,
)

logger = logging.getLogger(__name__)


class MistakeReviewChecker:
    """Nội dung của LLM chỉ được lưu khi: đúng lược đồ (đáp án nằm trong 4 lựa chọn khác nhau), câu luyện chứa
    từ cần học, không mâu thuẫn từ điển M06 và không khó hơn trình độ+1 (hoặc cấp của từ nếu từ khó hơn).
    Sai bất kỳ điều nào thì bỏ cả kết quả để dùng dự phòng."""

    def __init__(self, levels: ExampleLevelChecker) -> None:
        self._levels = levels

    async def validate(
        self, payload: object, word: QuizWord, learner_level: int | None
    ) -> MistakeReview | None:
        review = parse_llm_review(payload)
        practice = review.practice if review else None
        if review is None or practice is None:
            logger.warning("Giải thích lỗi sai của LLM sai lược đồ")
            return None
        if not practice_mentions_term(practice, word.term):
            logger.warning("Câu luyện của LLM không chứa từ cần học: %s", word.term)
            return None
        cleaned = clean_meaning_options(practice_as_question(practice, word.term))
        if cleaned is None or contradicts_dictionary(cleaned, word):
            logger.warning("Câu luyện của LLM mâu thuẫn từ điển: %s", word.term)
            return None
        fixed = with_cleaned_options(practice, cleaned)
        if fixed is None or not await self._easy_enough(fixed.prompt, word, learner_level):
            return None
        return MistakeReview(review.explanation, review.origin, review.difference, fixed)

    async def _easy_enough(self, prompt: str, word: QuizWord, learner_level: int | None) -> bool:
        runs = han_runs(prompt)
        if not runs:
            return True  # không có chữ Hán trong câu hỏi thì không có gì để đo
        (level,) = await self._levels.difficulties(["，".join(runs)])
        cap = max(example_difficulty_cap(learner_level, word.hsk_level), word.hsk_level or 0)
        if level is not None and level > cap:
            logger.warning("Câu luyện của LLM quá khó (HSK %s > %s)", level, cap)
            return False
        return True
