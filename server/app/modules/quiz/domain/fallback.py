"""Sinh đề dự phòng từ dữ liệu từ điển (F09.08): mỗi từ một câu, xen kẽ ba dạng."""

from __future__ import annotations

import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    NewQuestion,
    QuestionOrigin,
    QuestionType,
    QuizWord,
    WordContext,
)
from app.modules.quiz.domain.rules import OPTION_COUNT, normalize_answer, option_meaning

MASK = "～"  # che chữ Hán trong nghĩa để câu hỏi Việt→Hán không lộ đáp án
BLANK = "＿＿"
MAX_HSK_LEVEL = 9
NEIGHBOR_LEVELS_FETCHED = 3  # cấp của từ + hai cấp lân cận gần nhất được nạp sẵn làm nhiễu
_HAN_RUN = re.compile("[一-鿿㐀-䶿\U00020000-\U0002fa1f]+")
QUESTION_FORMS = 3  # Hán→Việt, Việt→Hán, điền từ


@dataclass(frozen=True, slots=True)
class DistractorPools:
    """Nguồn phương án nhiễu: từ HSK theo cấp (nạp từ từ điển) và các từ khác trong sổ tay (dự phòng cuối)."""

    by_level: Mapping[int, Sequence[DistractorCandidate]] = field(default_factory=dict)
    notebook: Sequence[DistractorCandidate] = ()


def level_order(level: int) -> list[int]:
    """Cấp HSK gần nhất trước: L, L-1, L+1, L-2, L+2, ... (F09.08 ngoại lệ: nhiễu ở cấp lân cận)."""
    ordered = [level]
    for step in range(1, MAX_HSK_LEVEL):
        ordered.extend(c for c in (level - step, level + step) if 1 <= c <= MAX_HSK_LEVEL)
    return ordered


def levels_to_fetch(level: int) -> list[int]:
    return level_order(level)[:NEIGHBOR_LEVELS_FETCHED]


def mask_han(text: str) -> str:
    return _HAN_RUN.sub(MASK, text)


def candidates_for(
    word: QuizWord, level: int, pools: DistractorPools, rng: random.Random
) -> list[DistractorCandidate]:
    """Ứng viên nhiễu theo thứ tự ưu tiên: cùng cấp, cấp lân cận, rồi từ khác trong sổ tay."""
    ordered: list[DistractorCandidate] = []
    for lv in level_order(level):
        group = [c for c in pools.by_level.get(lv, ()) if c.term != word.term]
        rng.shuffle(group)
        ordered.extend(group)
    others = [c for c in pools.notebook if c.term != word.term]
    rng.shuffle(others)
    return ordered + others


def pick_options(
    candidates: Sequence[DistractorCandidate], correct_meaning: str, *, by_meaning: bool
) -> list[str] | None:
    """Chọn đủ `OPTION_COUNT - 1` nhiễu không trùng nhau và không trùng nghĩa với đáp án đúng.

    Từ đồng nghĩa với đáp án bị loại ở cả hai chiều để câu hỏi chỉ có một đáp án đúng.
    """
    banned_meaning = normalize_answer(correct_meaning)
    seen: set[str] = {banned_meaning} if by_meaning else set()
    seen_terms: set[str] = set()
    chosen: list[str] = []
    for c in candidates:
        meaning = option_meaning(c.meaning_vi)
        if banned_meaning and normalize_answer(meaning) == banned_meaning:
            continue
        value = meaning if by_meaning else c.term
        key = normalize_answer(value)
        if not value or key in seen or c.term in seen_terms:
            continue
        seen.add(key)
        seen_terms.add(c.term)
        chosen.append(value)
        if len(chosen) == OPTION_COUNT - 1:
            return chosen
    return None


def _explanation(word: QuizWord, meaning: str) -> str:
    head = f"{word.term} ({word.pinyin})" if word.pinyin else word.term
    return f"{head}: {meaning}" if meaning else head


def _han_to_viet(
    word: QuizWord, meaning: str, level: int, pools: DistractorPools, rng: random.Random
) -> NewQuestion | None:
    if not meaning:
        return None
    wrong = pick_options(candidates_for(word, level, pools, rng), meaning, by_meaning=True)
    if wrong is None:
        return None
    options = [meaning, *wrong]
    rng.shuffle(options)
    return NewQuestion(
        QuestionType.MULTIPLE_CHOICE,
        f"“{word.term}” nghĩa là gì?",
        meaning,
        QuestionOrigin.FALLBACK,
        options=options,
        explanation=_explanation(word, meaning),
        vocab_entry_id=word.entry_id,
        term=word.term,
    )


def _viet_to_han(
    word: QuizWord, meaning: str, level: int, pools: DistractorPools, rng: random.Random
) -> NewQuestion | None:
    masked = mask_han(meaning)
    if not any(c.isalpha() for c in masked):  # nghĩa chỉ toàn chữ Hán: không còn gì để hỏi
        return None
    wrong = pick_options(candidates_for(word, level, pools, rng), meaning, by_meaning=False)
    if wrong is None:
        return None
    options = [word.term, *wrong]
    rng.shuffle(options)
    return NewQuestion(
        QuestionType.MULTIPLE_CHOICE,
        f"Từ nào có nghĩa “{masked}”?",
        word.term,
        QuestionOrigin.FALLBACK,
        options=options,
        explanation=_explanation(word, meaning),
        vocab_entry_id=word.entry_id,
        term=word.term,
    )


def _fill_blank_prompt(word: QuizWord, meaning: str, contexts: Sequence[WordContext]) -> str:
    for ctx in contexts:
        if word.term in ctx.sentence_zh:
            prompt = f"Điền chữ Hán vào chỗ trống: {ctx.sentence_zh.replace(word.term, BLANK)}"
            return f"{prompt}\nGợi ý: {ctx.sentence_vi}" if ctx.sentence_vi else prompt
    if word.pinyin and meaning:
        return f"Viết chữ Hán của “{word.pinyin}” ({mask_han(meaning)})"
    if word.pinyin:
        return f"Viết chữ Hán của “{word.pinyin}”"
    if meaning:
        return f"Viết chữ Hán có nghĩa “{mask_han(meaning)}”"
    return f"Gõ lại từ sau bằng chữ Hán: {word.term}"  # không còn dữ liệu nào để gợi ý


def _fill_blank(word: QuizWord, meaning: str, contexts: Sequence[WordContext]) -> NewQuestion:
    return NewQuestion(
        QuestionType.FILL_BLANK,
        _fill_blank_prompt(word, meaning, contexts),
        word.term,
        QuestionOrigin.FALLBACK,
        accepted_answers=[word.term],
        explanation=_explanation(word, meaning),
        vocab_entry_id=word.entry_id,
        term=word.term,
    )


def build_choice_question(
    word: QuizWord, index: int, pools: DistractorPools, default_level: int, rng: random.Random
) -> NewQuestion | None:
    """Câu trắc nghiệm theo định nghĩa (Hán→Việt hoặc Việt→Hán); None nếu thiếu nghĩa hoặc nhiễu.

    Dùng cho từ mở rộng (F09.09), vốn chỉ được hỏi dạng trắc nghiệm.
    """
    meaning = option_meaning(word.meaning_vi)
    level = word.hsk_level or default_level
    for shift in range(2):
        if (index + shift) % 2 == 0:
            question = _han_to_viet(word, meaning, level, pools, rng)
        else:
            question = _viet_to_han(word, meaning, level, pools, rng)
        if question is not None:
            return question
    return None


def build_fallback_question(
    word: QuizWord,
    index: int,
    contexts: Sequence[WordContext],
    pools: DistractorPools,
    default_level: int,
    rng: random.Random,
) -> NewQuestion:
    """Một câu dự phòng cho `word`; `index` quyết định dạng ưu tiên để ba dạng xen kẽ.

    Dạng ưu tiên không khả thi (thiếu nghĩa hoặc không đủ nhiễu) thì thử dạng kế; câu điền từ luôn khả thi.
    """
    meaning = option_meaning(word.meaning_vi)
    level = word.hsk_level or default_level
    for shift in range(QUESTION_FORMS):
        slot = (index + shift) % QUESTION_FORMS
        if slot == 0:
            question = _han_to_viet(word, meaning, level, pools, rng)
        elif slot == 1:
            question = _viet_to_han(word, meaning, level, pools, rng)
        else:
            return _fill_blank(word, meaning, contexts)
        if question is not None:
            return question
    return _fill_blank(word, meaning, contexts)


def build_fallback_questions(
    words: Sequence[QuizWord],
    contexts: Mapping[int, Sequence[WordContext]],
    pools: DistractorPools,
    default_level: int,
    rng: random.Random,
) -> list[NewQuestion]:
    return [
        build_fallback_question(w, i, contexts.get(w.entry_id, ()), pools, default_level, rng)
        for i, w in enumerate(words)
    ]
