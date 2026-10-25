"""Rà soát đề do LLM sinh trước khi dùng (F09.07 bước 2, F09.09): loại câu mâu thuẫn, kiểm câu ví dụ."""

from __future__ import annotations

import logging
import random
from collections.abc import Sequence
from dataclasses import replace

from app.modules.quiz.application.ports import ExampleLevelChecker, ExampleSource
from app.modules.quiz.domain.entities import NewQuestion, QuestionType, QuizWord
from app.modules.quiz.domain.examples import choose_example, example_difficulty_cap
from app.modules.quiz.domain.llm_review import (
    clean_meaning_options,
    contradicts_dictionary,
    example_acceptable,
    fill_blank_sentence,
    with_meaning_hint,
)
from app.modules.quiz.domain.llm_schema import LlmQuestions

logger = logging.getLogger(__name__)

EXAMPLE_FETCH_LIMIT = 30


class LlmReviewer:
    """Câu mâu thuẫn từ điển bị loại (người gọi bù câu dự phòng). Câu ví dụ của LLM chỉ được giữ khi chứa từ
    đang hỏi và có độ khó ≤ trình độ+1; không thì thay bằng câu Tatoeba cùng mức độ khó."""

    def __init__(self, checker: ExampleLevelChecker, examples: ExampleSource, rng: random.Random) -> None:
        self._checker = checker
        self._examples = examples
        self._rng = rng

    async def review(
        self,
        llm: LlmQuestions,
        words: Sequence[QuizWord],
        learner_level: int | None,
        used_example_ids: set[int],
    ) -> list[NewQuestion]:
        by_entry = {w.entry_id: w for w in words}
        kept = self._acceptable(llm, by_entry)
        dropped = len(llm.questions) - len(kept)
        if dropped:
            logger.warning("Loại %d câu LLM mâu thuẫn từ điển hoặc có phương án không dùng được", dropped)
        # Một lần tra độ khó cho cả câu ví dụ lẫn câu điền từ đã điền đáp án.
        sentences = _sentences_to_check(kept, llm)
        found = await self._checker.difficulties([text for _, _, text in sentences]) if sentences else []
        example_level: dict[int, int | None] = {}
        blank_level: dict[int, int | None] = {}
        for (kind, sentence_entry, _), level in zip(sentences, found, strict=True):
            (example_level if kind == "example" else blank_level)[sentence_entry] = level
        reviewed: list[NewQuestion] = []
        for question in kept:
            entry_id = question.vocab_entry_id
            word = by_entry[entry_id] if entry_id is not None else None
            if word is not None and question.question_type is QuestionType.FILL_BLANK:
                cap = example_difficulty_cap(learner_level, word.hsk_level)
                filled = fill_blank_sentence(question)
                if filled is None or not example_acceptable(
                    filled, word.term, blank_level.get(word.entry_id), cap
                ):
                    logger.warning("Loại câu điền từ của LLM không rõ nghĩa hoặc quá khó: %s", word.term)
                    continue
                question = with_meaning_hint(question, word)
            reviewed.append(
                await self._attach_example(
                    question, by_entry, llm, example_level, learner_level, used_example_ids
                )
            )
        return reviewed

    @staticmethod
    def _acceptable(llm: LlmQuestions, by_entry: dict[int, QuizWord]) -> list[NewQuestion]:
        kept: list[NewQuestion] = []
        for question in llm.questions:
            word = by_entry.get(question.vocab_entry_id) if question.vocab_entry_id is not None else None
            if word is None or contradicts_dictionary(question, word):
                continue
            cleaned = clean_meaning_options(question)
            if cleaned is not None:
                kept.append(cleaned)
        return kept

    async def _attach_example(
        self,
        question: NewQuestion,
        by_entry: dict[int, QuizWord],
        llm: LlmQuestions,
        difficulty: dict[int, int | None],
        learner_level: int | None,
        used_example_ids: set[int],
    ) -> NewQuestion:
        entry_id = question.vocab_entry_id
        word = by_entry.get(entry_id) if entry_id is not None else None
        if entry_id is None or word is None:
            return question
        cap = example_difficulty_cap(learner_level, word.hsk_level)
        example = llm.examples.get(entry_id)
        if example is not None and example_acceptable(example.zh, word.term, difficulty.get(entry_id), cap):
            text = f"Ví dụ: {example.zh} — {example.vi}" if example.vi else f"Ví dụ: {example.zh}"
            return replace(question, explanation="\n".join(filter(None, (question.explanation, text))))
        found = await self._examples.find(word.term, cap, EXAMPLE_FETCH_LIMIT)
        chosen = choose_example(found, word.term, used_example_ids, self._rng)
        if chosen is None:
            return question
        used_example_ids.add(chosen.id)
        return replace(question, example_id=chosen.id)


def _sentences_to_check(kept: Sequence[NewQuestion], llm: LlmQuestions) -> list[tuple[str, int, str]]:
    """(loại, mã mục từ, câu) cần tra độ khó: câu ví dụ của LLM và câu điền từ đã điền đáp án."""
    sentences: list[tuple[str, int, str]] = []
    for question in kept:
        entry_id = question.vocab_entry_id
        if entry_id is None:
            continue
        if entry_id in llm.examples:
            sentences.append(("example", entry_id, llm.examples[entry_id].zh))
        filled = fill_blank_sentence(question)
        if filled is not None:
            sentences.append(("blank", entry_id, filled))
    return sentences
