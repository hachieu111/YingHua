"""M09 - chất lượng đề (F09.07, F09.08, F09.09): cầu nối từ mở rộng, phương án nghĩa, câu điền từ LLM.

Mẫu nghĩa lấy từ `dict_entries.meanings_vi` thật (CVDICT) khi chạy thử 25/10/2026.
"""

from __future__ import annotations

import random
from typing import Any

from app.core.common_chars import COMMON_CHARS, is_common_char
from app.core.glosses import best_gloss, is_reference_meaning, short_meaning
from app.modules.quiz.application.llm_review import LlmReviewer
from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    ExampleRow,
    NewQuestion,
    QuestionOrigin,
    QuestionType,
    QuizWord,
    RelatedCandidate,
    RelatedLink,
    RelatedSource,
)
from app.modules.quiz.domain.examples import build_example_question
from app.modules.quiz.domain.fallback import DistractorPools, pick_options
from app.modules.quiz.domain.llm_review import (
    clean_meaning_options,
    fill_blank_sentence,
    with_meaning_hint,
)
from app.modules.quiz.domain.llm_schema import LlmQuestions
from app.modules.quiz.domain.related import build_hint, is_dictionary_backed
from app.modules.quiz.domain.rules import OPTION_MAX_CHARS
from app.modules.quiz.infrastructure.related import _saved_by_char
from tests.unit.quiz_fakes import FakeExamples


# --------------------------------------------------------------------------- D: nghĩa CVDICT
def test_short_meaning_drops_cvdict_pinyin_references() -> None:
    """Ký hiệu thô `繁|简[pinyin số]` và `[pinyin số]` không còn trong nghĩa hiển thị."""
    assert short_meaning("biến thể er hoá của 一塊|一块[yi1 kuai4]") == "biến thể er hoá của 一块"
    assert short_meaning("biến thể của 溯[su4]") == "biến thể của 溯"
    assert short_meaning("cái cưa (LT:把[ba3])") == "cái cưa (LT:把)"
    assert short_meaning("số báo cũ (viết tắt của 過期刊物|过期刊物[guo4 qi1 kan1 wu4])") == (
        "số báo cũ (viết tắt của 过期刊物)"
    )
    assert short_meaning("dùng trong 蓇葖[gu1tu1]") == "dùng trong 蓇葖"
    assert short_meaning("cái đó [ba3] nữa") == "cái đó nữa"
    assert "[" not in short_meaning("xem 開齋節|开斋节[Kai1zhai1jie2]")


def test_short_meaning_prefers_real_sense_over_reference_sense() -> None:
    assert short_meaning("biến thể của 溯[su4]; ngược dòng") == "ngược dòng"
    assert short_meaning("xem 筕篖[hang2 tang2]; ghế dài") == "ghế dài"
    assert short_meaning("xem 筕篖[hang2 tang2]") == "xem 筕篖"  # chỉ có tham chiếu thì giữ lại
    assert short_meaning("như thế nào") == "như thế nào"  # "như" không kèm chữ Hán là nghĩa thật


def test_best_gloss_skips_leading_reference_glosses() -> None:
    assert is_reference_meaning("biến thể của 溯[su4]") and not is_reference_meaning("một khối")
    assert best_gloss(["biến thể của 溯[su4]", "một khối", "một miếng"]) == "một khối"
    assert best_gloss(["xem 筕篖[hang2 tang2]"]) == "xem 筕篖[hang2 tang2]"
    assert best_gloss([None, ""]) == ""


# --------------------------------------------------------------------------- A: cầu nối
def test_common_chars_are_a_named_list_of_reasonable_size() -> None:
    assert 40 <= len(COMMON_CHARS) <= 60
    assert is_common_char("一") and is_common_char("的") and not is_common_char("朋")


def _word(entry_id: int, term: str, level: int | None = None, meaning: str | None = None) -> QuizWord:
    return QuizWord(entry_id, term, "py", meaning, level, "learning")


def test_common_chars_never_bridge_saved_words() -> None:
    saved = [_word(1, "一阶术"), _word(2, "朋友")]
    assert set(_saved_by_char(saved)) == {"阶", "术", "朋", "友"}  # 一 bị loại
    assert _saved_by_char([_word(3, "我们")]) == {}


def test_hint_never_names_a_common_char_as_the_shared_char() -> None:
    link = RelatedLink(RelatedSource.SHARED_CHAR, 1, "一阶术", None, "一")
    hint = build_hint(RelatedCandidate("一起", None, "cùng", 1, (link,), "nhất"))
    assert "chữ 一" not in hint and hint == "Gợi ý: âm Hán Việt là nhất"


def test_bridge_must_be_in_dictionary() -> None:
    assert is_dictionary_backed(2, None)
    assert is_dictionary_backed(None, "bạn bè")
    assert not is_dictionary_backed(None, None)
    assert not is_dictionary_backed(None, "[ái]")  # chỉ còn phần đọc Hán Việt, không phải nghĩa


# --------------------------------------------------------------------------- B: phương án nghĩa
LONG = "Thiên. Phàm một bài văn đoạn sách hay một thiên sách gồm nhiều chương mục đều gọi là thiên " * 2


def test_distractor_meanings_are_short_and_unique_after_normalisation() -> None:
    candidates = [
        DistractorCandidate("甲", LONG),
        DistractorCandidate("乙", "[ái] ① Bạn bè ② khác"),
        DistractorCandidate("丙", "bạn bè"),  # trùng "Bạn bè" sau chuẩn hóa
        DistractorCandidate("丁", "[ái]"),  # rỗng sau rút gọn
        DistractorCandidate("戊", "con mèo"),
        DistractorCandidate("己", "con chó"),
    ]
    options = pick_options(candidates, "đáp án", by_meaning=True)
    assert options is not None and len(options) == 3
    assert all(0 < len(o) <= OPTION_MAX_CHARS for o in options)
    assert len({o.casefold() for o in options}) == 3 and "" not in options


def test_translate_form_uses_short_distractors_and_skips_long_correct_sentence() -> None:
    word = _word(1, "朋友", 2, "bạn bè")
    pools = DistractorPools(
        {2: [DistractorCandidate(t, f"nghĩa {t}") for t in ("朋党", "学习", "老师", "同学")]}
    )
    translations = [LONG, "", "Câu A", "Câu A", "Câu B", "Câu C"]
    example = ExampleRow(1, "我喜欢朋友们", "py", "Tôi thích các bạn", 2)
    q = build_example_question(word, 2, example, 2, pools, translations, random.Random(1))
    assert q is not None and q.correct_answer == "Tôi thích các bạn"
    assert q.options is not None and all(len(o) <= OPTION_MAX_CHARS for o in q.options)
    assert len(set(q.options)) == 4
    too_long = ExampleRow(2, "我喜欢朋友们", "py", LONG, 2)
    q2 = build_example_question(word, 2, too_long, 2, pools, translations, random.Random(1))
    assert q2 is None or (q2.example_form is not None and q2.correct_answer != LONG)


def _choice(answer: str, options: list[str]) -> NewQuestion:
    return NewQuestion(
        QuestionType.MULTIPLE_CHOICE,
        "“学习” nghĩa là gì?",
        answer,
        QuestionOrigin.LLM,
        options=options,
        vocab_entry_id=1,
        term="学习",
    )


def test_llm_meaning_options_are_shortened_deduplicated_and_must_keep_the_answer() -> None:
    q = _choice("học tập", ["học tập", LONG, "Học tập", "[ái]", "ăn", "ngủ"])
    cleaned = clean_meaning_options(q)
    assert cleaned is not None and cleaned.correct_answer == "học tập"
    assert cleaned.options is not None
    assert all(len(o) <= OPTION_MAX_CHARS for o in cleaned.options)
    assert len({o.casefold() for o in cleaned.options}) == len(cleaned.options)
    assert clean_meaning_options(_choice("[ái]", ["[ái]", "a", "b"])) is None  # đáp án rỗng
    assert clean_meaning_options(_choice("học", ["học", "ăn"])) is None  # còn quá ít phương án
    han = _choice("学习", ["学习", "朋友", "老师"])
    assert clean_meaning_options(han) is han  # đáp án chữ Hán giữ nguyên


# --------------------------------------------------------------------------- E: câu điền từ LLM
def _fill(prompt: str, term: str = "朋友") -> NewQuestion:
    return NewQuestion(
        QuestionType.FILL_BLANK,
        prompt,
        term,
        QuestionOrigin.LLM,
        accepted_answers=[term],
        vocab_entry_id=2,
        term=term,
    )


def test_fill_blank_sentence_requires_exactly_one_blank() -> None:
    assert fill_blank_sentence(_fill("他是我的＿＿")) == "他是我的朋友"
    assert fill_blank_sentence(_fill("＿＿和＿＿")) is None
    assert fill_blank_sentence(_fill("没有空格")) is None


def test_meaning_hint_added_only_when_prompt_has_no_latin_text() -> None:
    word = _word(2, "朋友", 2, "bạn bè")
    bare = with_meaning_hint(_fill("这是＿＿的词语。"), word)
    assert bare.prompt == "这是＿＿的词语。\n(nghĩa: bạn bè)"
    unchanged = _fill("Điền từ: 他是我的＿＿")
    assert with_meaning_hint(unchanged, word) is unchanged
    no_meaning = with_meaning_hint(_fill("这是＿＿"), _word(2, "朋友", 2, None))
    assert no_meaning.prompt.endswith("(pinyin: py)")
    leaking = with_meaning_hint(_fill("这是＿＿"), _word(2, "朋友", 2, "bạn 朋友"))
    assert "朋友" not in leaking.prompt.split("\n", 1)[1]


class Levels:
    """Độ khó cố định theo từng câu được hỏi, ghi lại các câu đã nhận."""

    def __init__(self, *levels: int | None) -> None:
        self.levels = list(levels)
        self.seen: list[str] = []

    async def difficulties(self, sentences: Any) -> list[int | None]:
        self.seen.extend(sentences)
        return [self.levels.pop(0) for _ in sentences]


async def _review(questions: list[NewQuestion], levels: Levels) -> list[NewQuestion]:
    words = [_word(2, "朋友", 2, "bạn bè")]
    rng = random.Random(1)
    reviewer = LlmReviewer(levels, FakeExamples(), rng)
    return await reviewer.review(LlmQuestions(questions), words, 2, set())


async def test_reviewer_checks_filled_sentence_difficulty_and_adds_meaning_hint() -> None:
    levels = Levels(2)
    kept = await _review([_fill("这是＿＿的词语。")], levels)
    assert levels.seen == ["这是朋友的词语。"]  # "＿＿" thay bằng từ rồi mới kiểm độ khó
    assert [q.prompt for q in kept] == ["这是＿＿的词语。\n(nghĩa: bạn bè)"]


async def test_reviewer_drops_ambiguous_or_too_hard_fill_blank() -> None:
    assert await _review([_fill("＿＿和＿＿")], Levels()) == []  # hai chỗ trống: mơ hồ
    assert await _review([_fill("他是我的＿＿")], Levels(6)) == []  # độ khó 6 > trình độ + 1
    assert await _review([_fill("他是我的＿＿")], Levels(None)) == []  # không xác định được độ khó
