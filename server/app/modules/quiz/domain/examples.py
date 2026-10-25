"""Câu hỏi dựa trên câu ví dụ Tatoeba (F09.09, US-NH-69): chọn câu theo độ khó và dựng ba dạng câu hỏi."""

from __future__ import annotations

import random
from collections.abc import Collection, Sequence

from app.modules.quiz.domain.entities import (
    ExampleForm,
    ExampleRow,
    NewQuestion,
    QuestionOrigin,
    QuestionType,
    QuizWord,
)
from app.modules.quiz.domain.fallback import BLANK, DistractorPools, candidates_for, pick_options
from app.modules.quiz.domain.rules import OPTION_COUNT, OPTION_MAX_CHARS, normalize_answer, option_meaning

EXAMPLE_MIN_CHARS = 5
EXAMPLE_MAX_CHARS = 25
RECENT_QUIZZES_FOR_EXAMPLES = 5  # không lặp câu ví dụ đã dùng trong bấy nhiêu bài gần nhất
LEVEL_MARGIN = 1
MARK_OPEN, MARK_CLOSE = "【", "】"
_FORMS = (ExampleForm.CLOZE, ExampleForm.SENSE, ExampleForm.TRANSLATE)


def example_difficulty_cap(learner_level: int | None, word_level: int | None) -> int:
    """Độ khó tối đa của câu ví dụ: trình độ + 1; chưa khai báo thì max(cấp của từ, 1) + 1."""
    base = learner_level if learner_level is not None else max(word_level or 1, 1)
    return base + LEVEL_MARGIN


def choose_example(
    examples: Sequence[ExampleRow], term: str, recent_ids: Collection[int], rng: random.Random
) -> ExampleRow | None:
    """Câu chứa từ, dài 5-25 chữ, chưa dùng gần đây; ưu tiên câu có bản dịch Việt rồi bốc ngẫu nhiên."""
    usable = sorted(
        (
            e
            for e in examples
            if term in e.zh and EXAMPLE_MIN_CHARS <= len(e.zh) <= EXAMPLE_MAX_CHARS and e.id not in recent_ids
        ),
        key=lambda e: e.id,
    )
    with_translation = [e for e in usable if e.vi]
    candidates = with_translation or usable
    return rng.choice(candidates) if candidates else None


def _explanation(word: QuizWord, meaning: str, example: ExampleRow) -> str:
    head = f"{word.term} ({word.pinyin})" if word.pinyin else word.term
    if meaning:
        head = f"{head}: {meaning}"
    sentence = f"{example.zh} — {example.vi}" if example.vi else example.zh
    return f"{head}\n{sentence}"


def _question(
    word: QuizWord,
    meaning: str,
    example: ExampleRow,
    form: ExampleForm,
    prompt: str,
    correct: str,
    options: list[str],
) -> NewQuestion:
    return NewQuestion(
        QuestionType.MULTIPLE_CHOICE,
        prompt,
        correct,
        QuestionOrigin.FALLBACK,
        options=options,
        explanation=_explanation(word, meaning, example),
        vocab_entry_id=word.entry_id,
        term=word.term,
        example_id=example.id,
        example_form=form,
    )


def _cloze(
    word: QuizWord, meaning: str, example: ExampleRow, level: int, pools: DistractorPools, rng: random.Random
) -> NewQuestion | None:
    ordered = candidates_for(word, level, pools, rng)
    ordered.sort(key=lambda c: len(c.term) != len(word.term))  # ưu tiên nhiễu cùng số chữ (sắp xếp ổn định)
    wrong = pick_options(ordered, meaning, by_meaning=False)
    if wrong is None:
        return None
    options = [word.term, *wrong]
    rng.shuffle(options)
    prompt = f"Chọn từ điền vào chỗ trống:\n{example.zh.replace(word.term, BLANK)}"
    if example.vi:
        prompt += f"\nNghĩa của câu: {example.vi}"
    return _question(word, meaning, example, ExampleForm.CLOZE, prompt, word.term, options)


def _sense(
    word: QuizWord, meaning: str, example: ExampleRow, level: int, pools: DistractorPools, rng: random.Random
) -> NewQuestion | None:
    if not meaning:
        return None
    wrong = pick_options(candidates_for(word, level, pools, rng), meaning, by_meaning=True)
    if wrong is None:
        return None
    options = [meaning, *wrong]
    rng.shuffle(options)
    marked = example.zh.replace(word.term, f"{MARK_OPEN}{word.term}{MARK_CLOSE}")
    prompt = f"Trong câu sau, “{word.term}” nghĩa là gì?\n{marked}"
    return _question(word, meaning, example, ExampleForm.SENSE, prompt, meaning, options)


def _translate(
    word: QuizWord, meaning: str, example: ExampleRow, translations: Sequence[str], rng: random.Random
) -> NewQuestion | None:
    # Đáp án đúng không bị cắt ngắn (cắt làm hỏng nghĩa): câu dịch quá dài thì dạng này không khả thi.
    correct = option_meaning(example.vi)
    if not correct or len(example.vi or "") > OPTION_MAX_CHARS:
        return None
    seen = {normalize_answer(correct)}
    wrong: list[str] = []
    for text in translations:
        candidate = option_meaning(text)
        key = normalize_answer(candidate)
        if candidate and key not in seen:
            seen.add(key)
            wrong.append(candidate)
        if len(wrong) == OPTION_COUNT - 1:
            break
    if len(wrong) < OPTION_COUNT - 1:
        return None
    options = [correct, *wrong]
    rng.shuffle(options)
    marked = example.zh.replace(word.term, f"{MARK_OPEN}{word.term}{MARK_CLOSE}")
    prompt = f"Chọn bản dịch đúng của câu:\n{marked}"
    return _question(word, meaning, example, ExampleForm.TRANSLATE, prompt, correct, options)


def build_example_question(
    word: QuizWord,
    index: int,
    example: ExampleRow,
    level: int,
    pools: DistractorPools,
    translations: Sequence[str],
    rng: random.Random,
) -> NewQuestion | None:
    """Câu hỏi từ câu ví dụ, xen kẽ ba dạng theo `index`; dạng không khả thi thì thử dạng kế, hết thì None."""
    meaning = option_meaning(word.meaning_vi)
    for shift in range(len(_FORMS)):
        form = _FORMS[(index + shift) % len(_FORMS)]
        if form is ExampleForm.CLOZE:
            question = _cloze(word, meaning, example, level, pools, rng)
        elif form is ExampleForm.SENSE:
            question = _sense(word, meaning, example, level, pools, rng)
        else:
            question = _translate(word, meaning, example, translations, rng)
        if question is not None:
            return question
    return None
