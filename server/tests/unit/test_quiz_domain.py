"""M09 domain: nghĩa ngắn, chọn từ theo R, đề dự phòng, kiểm lược đồ LLM, chấm điểm.

US-NH-45 (chọn từ), US-NH-47 (chuẩn hóa đáp án), US-NH-50 (đề dự phòng), US-LLM-02 (lược đồ).
"""

from __future__ import annotations

import random

from app.core.glosses import short_meaning
from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    QuestionOrigin,
    QuestionType,
    QuizWord,
    WordContext,
)
from app.modules.quiz.domain.fallback import (
    BLANK,
    MASK,
    DistractorPools,
    build_fallback_questions,
    level_order,
    mask_han,
)
from app.modules.quiz.domain.llm_schema import validate_llm_payload
from app.modules.quiz.domain.rules import (
    HIGH_R_MIN,
    LOW_R_MAX,
    is_correct_answer,
    normalize_answer,
    quotas,
    select_words,
)


def _word(i: int, term: str | None = None, meaning: str | None = "nghĩa", level: int | None = 2) -> QuizWord:
    return QuizWord(i, term or f"词{i}", f"pin{i}", meaning, level, "learning")


def test_short_meaning_strips_brackets_senses_and_dash_runs() -> None:
    """F09.08: nghĩa ngắn bỏ [..] đầu, chỉ lấy ①, cắt sau dải gạch."""
    assert short_meaning("[hành, hạnh] ① Bước đi. ② Làm ra.") == "Bước đi"
    assert short_meaning("yêu; thích ------- ví dụ dài") == "yêu; thích"
    assert short_meaning(None) == ""
    assert short_meaning("[ái]") == ""


def test_short_meaning_cuts_at_word_boundary() -> None:
    text = "một hai ba bốn năm sáu bảy tám chín mười"
    cut = short_meaning(text, max_chars=20)
    assert len(cut) <= 20 and text.startswith(cut) and not cut.endswith(" ")
    assert cut == "một hai ba bốn năm"  # không xé đôi từ "sáu"


def test_quotas_split_sixty_thirty_ten() -> None:
    assert quotas(10) == (6, 3, 1)
    assert quotas(5) == (3, 2, 0)
    assert sum(quotas(17)) == 17


def test_select_words_follows_r_distribution_and_is_deterministic() -> None:
    low = [(_word(i), 0.1) for i in range(10)]
    mid = [(_word(100 + i), 0.8) for i in range(10)]
    high = [(_word(200 + i), 0.99) for i in range(10)]
    assert LOW_R_MAX == 0.7 and HIGH_R_MIN == 0.9
    picked = select_words(low + mid + high, 10, random.Random(1))
    ids = {w.entry_id for w in picked}
    assert len(picked) == 10
    assert len(ids & {w.entry_id for w, _ in low}) == 6
    assert len(ids & {w.entry_id for w, _ in mid}) == 3
    assert len(ids & {w.entry_id for w, _ in high}) == 1
    again = select_words(low + mid + high, 10, random.Random(1))
    assert [w.entry_id for w in picked] == [w.entry_id for w in again]


def test_select_words_fills_missing_group_from_lowest_remaining_r() -> None:
    scored = [(_word(i), 0.95) for i in range(8)] + [(_word(50), 0.2), (_word(51), 0.75)]
    picked = {w.entry_id for w in select_words(scored, 10, random.Random(3))}
    assert picked == {w.entry_id for w, _ in scored}
    few = select_words(scored, 4, random.Random(3))
    assert {50, 51} <= {w.entry_id for w in few}  # nhóm thấp/trung bình đủ, phần bù lấy từ R thấp nhất


def test_level_order_prefers_nearest_levels() -> None:
    assert level_order(3)[:5] == [3, 2, 4, 1, 5]
    assert level_order(1)[:3] == [1, 2, 3]
    assert sorted(level_order(9)) == list(range(1, 10))


def _pools() -> DistractorPools:
    same = [DistractorCandidate(f"同{i}", f"nghĩa lạ {i}") for i in range(6)]
    near = [DistractorCandidate(f"近{i}", f"nghĩa gần {i}") for i in range(6)]
    return DistractorPools({2: same, 3: near})


def test_fallback_questions_cycle_three_forms_without_leaking_answers() -> None:
    """US-NH-50: mỗi từ một câu, xen kẽ Hán→Việt, Việt→Hán, điền từ; nhiễu không trùng; che chữ Hán."""
    words = [_word(1, "学习", "học; học tập"), _word(2, "朋友", "bạn bè"), _word(3, "你好", "xin chào")]
    contexts = {3: [WordContext("他说你好吗", "Anh ấy hỏi thăm")]}
    qs = build_fallback_questions(words, contexts, _pools(), 2, random.Random(7))
    assert [q.question_type for q in qs] == [
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.FILL_BLANK,
    ]
    assert all(q.origin is QuestionOrigin.FALLBACK for q in qs)
    first, second, third = qs
    assert first.prompt == "“学习” nghĩa là gì?"
    assert first.correct_answer == "học; học tập" and first.options is not None
    assert len(first.options) == 4 and len(set(first.options)) == 4 and first.correct_answer in first.options
    assert second.correct_answer == "朋友" and second.options is not None
    assert len(set(second.options)) == 4 and "bạn bè" in second.prompt
    assert third.correct_answer == "你好" and third.accepted_answers == ["你好"]
    assert BLANK in third.prompt and "你好" not in third.prompt and "Anh ấy hỏi thăm" in third.prompt
    assert third.explanation == "你好 (pin3): xin chào"


def test_fallback_masks_han_in_meaning_and_skips_infeasible_forms() -> None:
    assert mask_han("Như 愛 cũ") == f"Như {MASK} cũ"
    # Không có nghĩa: chỉ còn dạng điền từ; không có ngữ cảnh thì dùng pinyin.
    [q] = build_fallback_questions([_word(1, "学习", None)], {}, _pools(), 2, random.Random(1))
    assert q.question_type is QuestionType.FILL_BLANK and "pin1" in q.prompt
    # Nghĩa toàn chữ Hán: Việt→Hán không khả thi nên lùi về dạng kế tiếp.
    [q2] = build_fallback_questions([_word(1, "学习", "愛")], {}, _pools(), 2, random.Random(1))
    assert q2.question_type is QuestionType.MULTIPLE_CHOICE and q2.correct_answer == "愛"


def test_fallback_distractors_skip_same_meaning_and_use_neighbor_levels() -> None:
    clash = [
        DistractorCandidate("同义", "Học"),
        *[DistractorCandidate(f"X{i}", f"nghĩa {i}") for i in range(2)],
    ]
    pools = DistractorPools({2: clash, 3: [DistractorCandidate("近", "nghĩa gần")]})
    [q] = build_fallback_questions([_word(1, "学习", "học")], {}, pools, 2, random.Random(2))
    assert q.options is not None and "Học" not in q.options and "nghĩa gần" in q.options


def test_fallback_uses_notebook_words_when_dictionary_is_short() -> None:
    notebook = [DistractorCandidate(f"本{i}", f"nghĩa sổ {i}") for i in range(5)]
    [q] = build_fallback_questions(
        [_word(1, "学习", "học")], {}, DistractorPools({}, notebook), 2, random.Random(2)
    )
    assert q.options is not None and len(q.options) == 4


def _payload(**override: object) -> dict[str, object]:
    q: dict[str, object] = {
        "term": "学习",
        "type": "multiple_choice",
        "prompt": "“学习”nghĩa là gì?",
        "options": ["học", "ăn", "ngủ", "chạy"],
        "answer": "học",
        "explanation": "học tập",
    }
    q.update(override)
    return {"questions": [q]}


def test_validate_llm_payload_accepts_valid_and_drops_unknown_terms() -> None:
    words = [_word(1, "学习")]
    ok = validate_llm_payload(_payload(), words)
    assert ok is not None and ok.questions[0].vocab_entry_id == 1
    assert ok.questions[0].origin is QuestionOrigin.LLM
    extra = _payload()
    extra["questions"] = [*extra["questions"], {**extra["questions"][0], "term": "朋友"}]  # type: ignore[index, list-item, dict-item]
    kept = validate_llm_payload(extra, words)
    assert kept is not None and len(kept.questions) == 1
    only_unknown = validate_llm_payload(_payload(term="朋友"), words)
    assert only_unknown is not None and only_unknown.questions == []


def test_validate_llm_payload_rejects_bad_schema() -> None:
    words = [_word(1, "学习")]
    for bad in (
        None,
        "not json",
        {},
        {"questions": []},
        {"questions": "x"},
        _payload(answer="không có trong lựa chọn"),
        _payload(type="essay"),
        _payload(options=["chỉ một"]),
        _payload(options=["a", "a", "b", "c"], answer="a"),
        _payload(prompt=""),
        _payload(explanation=5),
        _payload(accepted_answers="x"),
    ):
        assert validate_llm_payload(bad, words) is None, bad
    fill_with_options = _payload(type="fill_blank", answer="学习")
    assert validate_llm_payload(fill_with_options, words) is None
    fill = _payload(type="fill_blank", answer="学习", options=None)
    assert validate_llm_payload(fill, words) is not None


def test_grading_normalizes_whitespace_case_and_pinyin_spaces() -> None:
    """US-NH-47 TC4: cách viết tương đương được chấp nhận."""
    fill = QuestionType.FILL_BLANK
    mc = QuestionType.MULTIPLE_CHOICE
    assert normalize_answer("  Nǐ   HǍO ") == "nǐ hǎo"
    assert is_correct_answer(fill, "  学习 ", "学习", [])
    assert is_correct_answer(fill, "Nǐhǎo", "nǐ hǎo", [])
    assert is_correct_answer(fill, "学 习", "学习", ["学 习"])
    assert not is_correct_answer(fill, "学 习", "学习", [])
    assert is_correct_answer(mc, "Học  Tập", "học tập", [])
    assert not is_correct_answer(mc, "hoctap", "học tập", [])
    assert not is_correct_answer(mc, None, "học", [])
    assert not is_correct_answer(fill, "   ", "学习", [])
