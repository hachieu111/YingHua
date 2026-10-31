"""M09 mở rộng F09.09 (US-NH-69): từ mở rộng, câu ví dụ theo độ khó, ba dạng câu mới, điểm riêng.

Không cần CSDL: dùng bản giả của nguồn câu ví dụ và nguồn ứng viên.
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.core.ai_policy import StaticAiPolicy
from app.modules.dictionary.domain.difficulty import example_difficulty, token_level
from app.modules.quiz.api.schemas import QuizDetailResponse
from app.modules.quiz.application.config import QuizConfig
from app.modules.quiz.application.drafting import FallbackQuestionBuilder, QuizDrafter
from app.modules.quiz.application.dto import AnswerInput, CreateQuizCommand
from app.modules.quiz.application.use_cases.create_quiz import CreateQuizUseCase
from app.modules.quiz.application.use_cases.get_quiz import GetQuizUseCase
from app.modules.quiz.application.use_cases.save_quiz_word import SaveQuizWordUseCase
from app.modules.quiz.application.use_cases.submit_quiz import SubmitQuizUseCase
from app.modules.quiz.domain.entities import (
    DistractorCandidate,
    ExampleForm,
    ExampleRow,
    QuestionType,
    QuizWord,
    RelatedCandidate,
    RelatedLink,
    RelatedSource,
    TargetKind,
)
from app.modules.quiz.domain.errors import (
    QuizNotFoundError,
    QuizNotSubmittedError,
    QuizQuestionNotFoundError,
    WordNotSavableError,
)
from app.modules.quiz.domain.examples import (
    build_example_question,
    choose_example,
    example_difficulty_cap,
)
from app.modules.quiz.domain.fallback import DistractorPools
from app.modules.quiz.domain.related import (
    build_hint,
    candidate_score,
    max_level_for,
    pick_related,
    related_count,
)
from app.modules.review.application.public import EstimateRetrievabilityUseCase, RescheduleCardsNowUseCase
from app.modules.review.domain.entities import Card, CardType, Rating
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
from app.modules.vocab.application.public import SaveWordCommand
from tests.conftest import FixedClock
from tests.unit.quiz_fakes import (
    FakeDistractors,
    FakeExamples,
    FakeGenerator,
    FakeProfiles,
    FakeQuizRepo,
    FakeQuizUow,
    FakeQuizVocab,
    FakeRelated,
)
from tests.unit.review_fakes import identity

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
CONFIG = QuizConfig(question_count=10, min_words=10)
LLM_OFF = StaticAiPolicy(False, 2)


def _word(i: int, term: str | None = None, meaning: str | None = "nghĩa", level: int | None = 2) -> QuizWord:
    return QuizWord(i, term or f"词{i}", f"pin{i}", meaning, level, "learning")


def _example(i: int, zh: str, vi: str | None = "bản dịch", level: int = 2) -> ExampleRow:
    return ExampleRow(i, zh, f"py{i}", vi, level)


def _candidate(
    term: str, source: RelatedSource = RelatedSource.SHARED_CHAR, bridge: QuizWord | None = None
) -> RelatedCandidate:
    bridge = bridge or _word(1, "朋友", "bạn bè")
    link = RelatedLink(source, bridge.entry_id, bridge.term, bridge.meaning_vi, "友")
    return RelatedCandidate(term, "pin", "nghĩa mở rộng", 2, (link,), han_viet="hữu")


# --------------------------------------------------------------------------- domain
def test_related_count_is_fifteen_percent_rounded_half_up() -> None:
    assert [related_count(n) for n in (3, 4, 5, 10, 20)] == [0, 1, 1, 2, 3]


def test_max_level_uses_declared_level_or_bridge_level_capped_at_three() -> None:
    assert max_level_for(4, 1) == 5  # đã khai báo: trình độ + 1
    assert max_level_for(None, 1) == 2  # chưa khai báo: cấp từ đã lưu + 1
    assert max_level_for(None, 6) == 3  # mặc định tối đa HSK 3
    assert max_level_for(None, None) == 2


def test_candidate_score_adds_distinct_sources_with_shared_char_strongest() -> None:
    bridge = _word(1, "朋友")
    strong = _candidate("友谊", RelatedSource.SHARED_CHAR, bridge)
    weak = _candidate("同级", RelatedSource.SAME_LEVEL, bridge)
    both = RelatedCandidate(
        "遇见",
        None,
        "gặp",
        2,
        (
            RelatedLink(RelatedSource.SAME_LEVEL, 1, "朋友"),
            RelatedLink(RelatedSource.ENCOUNTERED, 1, "朋友", None, "Hoa Hồng"),
        ),
    )
    assert candidate_score(strong) > candidate_score(weak)
    assert candidate_score(both) == candidate_score(weak) + 3.0


def test_pick_related_is_weighted_unique_and_deterministic() -> None:
    candidates = [_candidate(f"友{i}", RelatedSource.SHARED_CHAR) for i in range(6)] + [
        _candidate(f"同{i}", RelatedSource.SAME_LEVEL) for i in range(20)
    ]
    first = pick_related(candidates, 2, random.Random(4))
    again = pick_related(candidates, 2, random.Random(4))
    assert [c.term for c in first] == [c.term for c in again]
    assert len({c.term for c in first}) == 2 and all(c.term.startswith("友") for c in first)
    assert len(pick_related(candidates[:1], 2, random.Random(1))) == 1  # thiếu ứng viên: trả những gì có
    assert pick_related(candidates, 0, random.Random(1)) == []


def test_build_hint_by_source_never_contains_the_answer_term() -> None:
    bridge = _word(1, "朋友", "bạn bè; bằng hữu")
    shared = build_hint(_candidate("友谊", RelatedSource.SHARED_CHAR, bridge))
    assert shared == "Gợi ý: chữ 友 giống trong 朋友 (bạn bè; bằng hữu) của bạn"
    met = RelatedCandidate(
        "遇见", None, "gặp", 2, (RelatedLink(RelatedSource.ENCOUNTERED, 1, "朋友", None, "Hoa Hồng"),)
    )
    assert build_hint(met) == "Gợi ý: từ này bạn đã gặp ở Hoa Hồng"
    component = _candidate("清洁", RelatedSource.SHARED_COMPONENT, bridge)
    assert "thành phần" in build_hint(component)
    level = RelatedCandidate(
        "同级", None, "x", 2, (RelatedLink(RelatedSource.SAME_LEVEL, 1, "朋友"),), "đồng"
    )
    assert build_hint(level) == "Gợi ý: âm Hán Việt là đồng"
    assert "遇见" not in build_hint(met) and "友谊" not in shared


def test_example_cap_and_choice_follow_difficulty_length_and_history() -> None:
    assert example_difficulty_cap(3, 5) == 4
    assert example_difficulty_cap(None, 2) == 3
    assert example_difficulty_cap(None, None) == 2
    examples = [
        _example(1, "我喜欢朋友", None),
        _example(2, "他是我的好朋友们", "Anh ấy là bạn tốt"),
        _example(3, "朋友", "quá ngắn"),
        _example(4, "朋友" + "很好" * 15, "quá dài"),
        _example(5, "没有这个词的句子"),
    ]
    rng = random.Random(0)
    assert choose_example(examples, "朋友", set(), rng).id == 2  # ưu tiên câu có bản dịch Việt  # type: ignore[union-attr]
    assert choose_example(examples, "朋友", {2}, rng).id == 1  # type: ignore[union-attr]
    assert choose_example(examples, "朋友", {1, 2}, rng) is None  # hết: người gọi lùi về dạng cũ


def test_example_difficulty_uses_highest_level_with_component_fallback() -> None:
    levels = {"我": 1, "喜欢": 1, "朋友": 2, "学": 1, "校": 2}
    assert example_difficulty(["我", "喜欢", "朋友", "。"], levels) == 2
    assert token_level("学校", levels) == 2  # không có từ: lấy cấp cao nhất của chữ cấu thành
    assert token_level("魑魅", levels) == 7  # không có gì: 7
    assert example_difficulty(["，", "abc"], levels) is None


def _pools() -> DistractorPools:
    same = [DistractorCandidate(t, f"nghĩa {t}") for t in ("朋党", "学习", "老师", "同学", "友情", "明白")]
    return DistractorPools({2: same})


def _make(form: ExampleForm, example: ExampleRow, translations: list[str] | None = None) -> Any:
    word = _word(1, "朋友", "bạn bè")
    index = list(ExampleForm).index(form)
    return build_example_question(
        word,
        index,
        example,
        2,
        _pools(),
        translations or ["bản dịch A", "bản dịch B", "bản dịch C"],
        random.Random(3),
    )


def test_cloze_question_hides_term_prefers_same_length_options_and_keeps_translation_hint() -> None:
    q = _make(ExampleForm.CLOZE, _example(9, "我喜欢朋友们", "Tôi thích các bạn"))
    assert q.example_form is ExampleForm.CLOZE and q.question_type is QuestionType.MULTIPLE_CHOICE
    assert "朋友" not in q.prompt and "＿＿" in q.prompt and "Tôi thích các bạn" in q.prompt
    assert q.correct_answer == "朋友" and len(q.options) == 4 and len(set(q.options)) == 4
    assert all(len(o) == 2 for o in q.options)  # nhiễu cùng số chữ
    assert q.example_id == 9 and q.term == "朋友" and q.vocab_entry_id == 1


def test_sense_question_marks_term_and_offers_meanings() -> None:
    q = _make(ExampleForm.SENSE, _example(9, "我喜欢朋友们"))
    assert q.example_form is ExampleForm.SENSE
    assert "我喜欢【朋友】们" in q.prompt and q.correct_answer == "bạn bè"
    assert "bạn bè" in q.options and len(q.options) == 4


def test_translate_question_needs_translation_and_never_puts_answer_in_prompt() -> None:
    q = _make(ExampleForm.TRANSLATE, _example(9, "我喜欢朋友们", "Tôi thích các bạn"))
    assert q.example_form is ExampleForm.TRANSLATE and q.correct_answer == "Tôi thích các bạn"
    assert "Tôi thích các bạn" not in q.prompt and "【朋友】" in q.prompt
    assert "Tôi thích các bạn" in q.options and len(set(q.options)) == 4
    # Không có vi (hoặc thiếu bản dịch nhiễu): lùi sang dạng khả thi kế tiếp.
    fallback = _make(ExampleForm.TRANSLATE, _example(9, "我喜欢朋友们", None))
    assert fallback.example_form is ExampleForm.CLOZE
    few = _make(ExampleForm.TRANSLATE, _example(9, "我喜欢朋友们", "Tôi thích"), translations=["chỉ một"])
    assert few.example_form is not ExampleForm.TRANSLATE


# --------------------------------------------------------------------------- use case
def _words(n: int = 12) -> list[QuizWord]:
    return [_word(i, f"词{i}", f"nghĩa {i}") for i in range(1, n + 1)]


class Env:
    def __init__(
        self,
        words: list[QuizWord],
        related: list[RelatedCandidate] | None = None,
        examples: dict[str, list[ExampleRow]] | None = None,
        translations: list[str] | None = None,
    ) -> None:
        self.vocab = FakeQuizVocab(words)
        self.repo = FakeQuizRepo()
        self.examples = FakeExamples(examples or {}, translations or [f"dịch nhiễu {i}" for i in range(8)])
        self.uow = FakeQuizUow(self.vocab, self.repo, examples=self.examples)
        self.clock = FixedClock(NOW)
        self.rng = random.Random(8)
        self.related = FakeRelated(related)
        drafter = QuizDrafter(
            FakeGenerator(), FallbackQuestionBuilder(FakeDistractors(), self.examples, self.rng), 0.5
        )
        self.create = CreateQuizUseCase(
            lambda: self.uow,
            FakeProfiles(),
            drafter,
            self.related,
            EstimateRetrievabilityUseCase(FsrsScheduler(enable_fuzzing=False)),
            CONFIG,
            LLM_OFF,
            self.clock,
            self.rng,
        )
        self.submit = SubmitQuizUseCase(lambda: self.uow, RescheduleCardsNowUseCase(), self.clock)
        self.get = GetQuizUseCase(lambda: self.uow)
        self.me = identity(1)

    def add_cards(self, entry_id: int) -> None:
        scheduler = FsrsScheduler(enable_fuzzing=False)
        yesterday = NOW - timedelta(days=1)
        reviewed = scheduler.review(scheduler.new_state(yesterday), Rating.GOOD, yesterday)
        schedule = replace(reviewed, due_at=NOW + timedelta(days=9))
        cards = self.uow.cards.items
        for card_type in CardType:
            card_id = len(cards) + 1
            cards[card_id] = Card(card_id, 1, entry_id, card_type, schedule, 1, 0, False, NOW, NOW)


def _related_set(n: int) -> list[RelatedCandidate]:
    return [_candidate(f"友谊{chr(0x4E00 + i)}", RelatedSource.SHARED_CHAR) for i in range(n)]


def _examples_for(terms: list[str], per_term: int = 2) -> dict[str, list[ExampleRow]]:
    rows: dict[str, list[ExampleRow]] = {}
    for t_index, term in enumerate(terms):
        rows[term] = [
            _example(100 * (t_index + 1) + k, f"这是{term}的句子{k}号", f"Câu {term} số {k}")
            for k in range(per_term)
        ]
    return rows


async def test_quiz_has_fifteen_percent_related_questions_with_hints() -> None:
    """F09.09: 10 câu → 8 câu từ đã lưu + 2 câu từ mở rộng (trắc nghiệm, có gợi ý, không đụng sổ tay)."""
    related = _related_set(5)
    env = Env(_words(), related, _examples_for([c.term for c in related]))
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    saved = [q for q in detail.questions if q.target_kind is TargetKind.SAVED]
    extra = [q for q in detail.questions if q.target_kind is TargetKind.RELATED]
    assert (len(saved), len(extra)) == (8, 2)
    assert (detail.quiz.question_count, detail.quiz.related_count) == (8, 2)
    assert {q.term for q in extra} <= {c.term for c in related}
    for q in extra:
        assert q.question_type is QuestionType.MULTIPLE_CHOICE and q.vocab_entry_id is None
        assert q.related_entry_id == 1 and q.hint and q.hint not in q.prompt
        assert q.hint.startswith("Gợi ý: chữ 友 giống trong 朋友")
    assert all(q.vocab_entry_id is not None and q.hint is None for q in saved)


async def test_missing_related_candidates_are_replaced_by_saved_words() -> None:
    none = Env(_words())
    detail = await none.create.execute(none.me, CreateQuizCommand(10))
    assert (detail.quiz.question_count, detail.quiz.related_count) == (10, 0)
    one = Env(_words(), _related_set(1), _examples_for([_related_set(1)[0].term]))
    detail = await one.create.execute(one.me, CreateQuizCommand(10))
    assert (detail.quiz.question_count, detail.quiz.related_count) == (9, 1)
    assert len(detail.questions) == 10


async def test_failing_related_source_does_not_block_the_quiz() -> None:
    env = Env(_words())

    async def boom(*args: object) -> list[RelatedCandidate]:
        raise RuntimeError("lỗi nguồn ứng viên")

    env.related.candidates = boom  # type: ignore[method-assign]
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    assert (detail.quiz.question_count, detail.quiz.related_count) == (10, 0)


async def test_examples_respect_difficulty_cap_and_are_not_repeated_in_five_recent_quizzes() -> None:
    """Cấp tối đa = trình độ + 1 (hồ sơ giả: HSK 2 → 3); không lặp câu của 5 bài gần nhất."""
    words = _words(10)
    rows = _examples_for([w.term for w in words], per_term=2)
    rows["词1"].append(_example(999, "这是词1的难句子", level=6))  # quá khó: không được chọn
    env = Env(words, examples=rows)
    first = await env.create.execute(env.me, CreateQuizCommand(10))
    second = await env.create.execute(env.me, CreateQuizCommand(10))
    ids1 = {q.example_id for q in first.questions if q.example_id}
    ids2 = {q.example_id for q in second.questions if q.example_id}
    assert len(ids1) == len(ids2) == 10 and not ids1 & ids2
    assert 999 not in ids1 | ids2
    assert all(cap == 3 for _, cap in env.examples.find_calls)
    third = await env.create.execute(env.me, CreateQuizCommand(10))  # hết câu mới: lùi về dạng cũ
    assert all(q.example_id is None for q in third.questions)
    assert all(q.vocab_entry_id for q in third.questions)


async def test_saved_word_without_examples_falls_back_to_context_then_definition() -> None:
    words = _words(10)
    env = Env(words)
    env.vocab.ctx[1] = []
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    assert all(q.example_id is None and q.example_form is None for q in detail.questions)
    assert {q.question_type for q in detail.questions} <= {
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.FILL_BLANK,
    }


async def test_pre_submit_response_does_not_leak_answers_for_new_forms() -> None:
    """US-NH-69: dạng điền từ không trả câu gốc, dạng dịch câu không trả `vi`; không có term/đáp án."""
    words = _words(10)
    env = Env(words, examples=_examples_for([w.term for w in words]))
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    body = QuizDetailResponse.from_detail(detail).model_dump(exclude_unset=True)
    forms = {q.example_form for q in detail.questions}
    assert forms == set(ExampleForm)  # đủ ba dạng xen kẽ
    by_id = {q.id: q for q in detail.questions}
    for item in body["questions"]:
        assert not {"term", "correct_answer", "related_to", "can_save", "is_correct", "explanation"} & set(
            item
        )
        form = by_id[item["id"]].example_form
        if form is ExampleForm.CLOZE:
            assert item["example"] is None
        else:
            assert set(item["example"]) == {"zh", "pinyin"}  # không có vi
        assert item["target_kind"] == "saved" and item["hint"] is None


async def test_scores_are_separate_and_related_answers_never_touch_srs() -> None:
    """F09.04 chỉ cho câu từ đã lưu; câu từ mở rộng có điểm riêng, đúng hay sai đều không đổi thẻ."""
    related = _related_set(3)
    words = _words()
    env = Env(words, related, _examples_for([c.term for c in related]))
    for w in words:
        env.add_cards(w.entry_id)
    before = {c.id: c.schedule.due_at for c in env.uow.cards.items.values()}
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    answers = []
    for q in detail.questions:
        # Đúng hết câu từ mở rộng, sai hết câu từ đã lưu.
        answers.append(AnswerInput(q.id, q.correct_answer if q.target_kind is TargetKind.RELATED else "sai"))
    result = await env.submit.execute(env.me, detail.quiz.id, answers)
    assert (result.quiz.score, result.quiz.related_score) == (0, 2)
    assert (result.quiz.question_count, result.quiz.related_count) == (8, 2)
    wrong_entries = {q.vocab_entry_id for q in result.questions if q.target_kind is TargetKind.SAVED}
    for card in env.uow.cards.items.values():
        if card.vocab_entry_id in wrong_entries:
            assert card.schedule.due_at == NOW
        else:
            assert card.schedule.due_at == before[card.id]  # từ không ra đề không bị đụng
    assert len(env.uow.cards.items) == 36  # không tạo thẻ mới cho từ mở rộng
    assert set(result.rescheduled_terms) == {w.term for w in words if w.entry_id in wrong_entries}
    assert related[0].term not in result.rescheduled_terms

    # Câu từ mở rộng làm sai cũng không đụng lịch ôn.
    env2 = Env(words, related, _examples_for([c.term for c in related]))
    for w in words:
        env2.add_cards(w.entry_id)
    detail2 = await env2.create.execute(env2.me, CreateQuizCommand(10))
    answers2 = [
        AnswerInput(q.id, q.correct_answer if q.target_kind is TargetKind.SAVED else "sai")
        for q in detail2.questions
    ]
    result2 = await env2.submit.execute(env2.me, detail2.quiz.id, answers2)
    assert (result2.quiz.score, result2.quiz.related_score) == (8, 0)
    assert all(c.schedule.due_at == NOW + timedelta(days=9) for c in env2.uow.cards.items.values())
    assert result2.rescheduled_terms == []


async def test_after_submit_reveals_term_bridge_example_and_can_save() -> None:
    related = _related_set(2)
    env = Env(_words(), related, _examples_for([c.term for c in related]))
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    result = await env.submit.execute(env.me, detail.quiz.id, [])
    # Bài đã nộp nhưng "朋友" (cầu nối) không nằm trong sổ tay giả của Env: related_to vắng.
    body = QuizDetailResponse.from_detail(result).model_dump(exclude_unset=True)
    related_items = [q for q in body["questions"] if q["target_kind"] == "related"]
    assert len(related_items) == 2
    for item in related_items:
        assert item["term"] in {c.term for c in related} and item["can_save"] is True
        assert item["correct_answer"] and "vi" in (item["example"] or {"vi": None})
    env.vocab.extra_saved.add(related_items[0]["term"])  # đã lưu rồi thì không còn nút lưu
    again = QuizDetailResponse.from_detail(await env.get.execute(env.me, detail.quiz.id)).model_dump(
        exclude_unset=True
    )
    flags = {q["term"]: q["can_save"] for q in again["questions"] if q["target_kind"] == "related"}
    assert flags[related_items[0]["term"]] is False and flags[related_items[1]["term"]] is True


class FakeSaver:
    def __init__(self) -> None:
        self.commands: list[SaveWordCommand] = []

    async def execute(self, identity: Any, command: SaveWordCommand) -> Any:
        self.commands.append(command)
        return "saved"


async def test_save_word_only_for_related_questions_of_submitted_quizzes() -> None:
    related = _related_set(2)
    env = Env(_words(), related, _examples_for([c.term for c in related]))
    saver = FakeSaver()
    use_case = SaveQuizWordUseCase(lambda: env.uow, saver)  # type: ignore[arg-type]
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    extra = next(q for q in detail.questions if q.target_kind is TargetKind.RELATED)
    saved_q = next(q for q in detail.questions if q.target_kind is TargetKind.SAVED)

    with pytest.raises(QuizNotSubmittedError):
        await use_case.execute(env.me, detail.quiz.id, extra.id)
    await env.submit.execute(env.me, detail.quiz.id, [])
    with pytest.raises(WordNotSavableError):
        await use_case.execute(env.me, detail.quiz.id, saved_q.id)
    with pytest.raises(QuizQuestionNotFoundError):
        await use_case.execute(env.me, detail.quiz.id, 987654)
    with pytest.raises(QuizNotFoundError):
        await use_case.execute(identity(2), detail.quiz.id, extra.id)
    assert saver.commands == []

    assert await use_case.execute(env.me, detail.quiz.id, extra.id) == "saved"
    assert saver.commands == [SaveWordCommand(extra.term, "quiz")]
