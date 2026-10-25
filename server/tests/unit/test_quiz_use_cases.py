"""M09 — use case với bản giả: F09.01, F09.03, F09.04, F09.06–F09.08, F13.07 (không cần CSDL hay LLM thật)."""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import PermissionDeniedError
from app.modules.quiz.application.config import QuizConfig
from app.modules.quiz.application.drafting import FallbackQuestionBuilder, QuizDrafter
from app.modules.quiz.application.dto import AnswerInput, CreateQuizCommand
from app.modules.quiz.application.use_cases.create_quiz import CreateQuizUseCase
from app.modules.quiz.application.use_cases.delete_quiz import DeleteQuizUseCase
from app.modules.quiz.application.use_cases.get_quiz import GetQuizUseCase
from app.modules.quiz.application.use_cases.list_quizzes import ListQuizzesUseCase
from app.modules.quiz.application.use_cases.submit_quiz import SubmitQuizUseCase
from app.modules.quiz.domain.entities import (
    FallbackReason,
    QuestionOrigin,
    QuizSource,
    QuizStatus,
    QuizWord,
)
from app.modules.quiz.domain.errors import (
    InvalidQuestionCountError,
    InvalidQuizAnswersError,
    NotEnoughWordsForQuizError,
    QuizAlreadySubmittedError,
    QuizGeneratorUnavailableError,
    QuizNotFoundError,
)
from app.modules.review.application.public import EstimateRetrievabilityUseCase, RescheduleCardsNowUseCase
from app.modules.review.domain.entities import Card, CardType, Rating
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
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
from tests.unit.review_fakes import admin_identity, identity

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
CONFIG = QuizConfig(question_count=10, min_words=10, daily_llm_limit=2, llm_enabled=False)


def _words(n: int = 12) -> list[QuizWord]:
    return [QuizWord(i, f"词{i}", f"pin{i}", f"nghĩa {i}", 2, "learning") for i in range(1, n + 1)]


def _llm_payload(words: list[QuizWord], skip: set[int] | None = None) -> dict[str, object]:
    questions = []
    for w in words:
        if skip and w.entry_id in skip:
            continue
        questions.append(
            {
                "term": w.term,
                "type": "multiple_choice",
                "prompt": f"“{w.term}” nghĩa là gì?",
                "options": [w.meaning_vi, "x1", "x2", "x3"],
                "answer": w.meaning_vi,
                "explanation": "giải thích",
            }
        )
    return {"questions": questions}


class Env:
    def __init__(
        self, words: list[QuizWord], generator: FakeGenerator | None = None, config: QuizConfig = CONFIG
    ) -> None:
        self.vocab = FakeQuizVocab(words)
        self.repo = FakeQuizRepo()
        self.uow = FakeQuizUow(self.vocab, self.repo)
        self.clock = FixedClock(NOW)
        self.generator = generator or FakeGenerator()
        self.rng = random.Random(5)
        drafter = QuizDrafter(
            self.generator, FallbackQuestionBuilder(FakeDistractors(), FakeExamples(), self.rng), 0.5
        )
        self.create = CreateQuizUseCase(
            lambda: self.uow,
            FakeProfiles(),
            drafter,
            FakeRelated(),
            EstimateRetrievabilityUseCase(FsrsScheduler(enable_fuzzing=False)),
            config,
            self.clock,
            self.rng,
        )
        self.submit = SubmitQuizUseCase(lambda: self.uow, RescheduleCardsNowUseCase(), self.clock)
        self.get = GetQuizUseCase(lambda: self.uow)
        self.me = identity(1)

    def add_cards(self, entry_id: int, *, due_in_days: int = 5, suspended: bool = False) -> None:
        """Ba thẻ vừa được ôn "Được" hôm qua (S đã có, R cao), đến hạn sau `due_in_days` ngày."""
        scheduler = FsrsScheduler(enable_fuzzing=False)
        yesterday = NOW - timedelta(days=1)
        reviewed = scheduler.review(scheduler.new_state(yesterday), Rating.GOOD, yesterday)
        schedule = replace(reviewed, due_at=NOW + timedelta(days=due_in_days))
        cards = self.uow.cards.items
        for card_type in CardType:
            card_id = len(cards) + 1
            cards[card_id] = Card(card_id, 1, entry_id, card_type, schedule, 1, 0, suspended, NOW, NOW)


async def test_create_quiz_requires_minimum_words() -> None:
    """US-NH-45 TC2: dưới 10 từ thì từ chối kèm số từ hiện có; từ Bỏ qua không tính."""
    env = Env(_words(12))
    env.vocab.status[1] = env.vocab.status[2] = env.vocab.status[3] = "ignored"
    with pytest.raises(NotEnoughWordsForQuizError) as exc:
        await env.create.execute(env.me, CreateQuizCommand())
    assert exc.value.details == {"current": 9, "required": 10}
    assert "10" in exc.value.message
    assert env.repo.quizzes == {}


async def test_create_quiz_rejects_bad_question_count() -> None:
    env = Env(_words())
    for bad in (4, 21):
        with pytest.raises(InvalidQuestionCountError):
            await env.create.execute(env.me, CreateQuizCommand(bad))


async def test_create_quiz_with_llm_disabled_uses_fallback_immediately() -> None:
    """US-NH-50 TC4: LLM tắt → đề dự phòng ngay, không gọi dịch vụ ngoài; có ghi chú."""
    gen = FakeGenerator()
    env = Env(_words(), gen)
    detail = await env.create.execute(env.me, CreateQuizCommand())
    assert gen.requests == []
    assert detail.quiz.source is QuizSource.FALLBACK
    assert detail.quiz.fallback_reason is FallbackReason.LLM_DISABLED
    assert detail.quiz.note == "Đề tạo tự động từ từ điển"
    assert detail.quiz.status is QuizStatus.IN_PROGRESS
    assert len(detail.questions) == 10 == detail.quiz.question_count
    assert len({q.vocab_entry_id for q in detail.questions}) == 10  # mỗi từ đúng một câu
    assert all(q.origin is QuestionOrigin.FALLBACK for q in detail.questions)


async def test_create_quiz_limits_questions_to_available_words() -> None:
    env = Env(_words(10))
    detail = await env.create.execute(env.me, CreateQuizCommand(20))
    assert len(detail.questions) == 10


LLM_ON = QuizConfig(10, 10, 2, True)


async def test_llm_valid_payload_makes_llm_quiz_without_fallback_note() -> None:
    words = _words()
    env = Env(words, FakeGenerator(), LLM_ON)

    # Dùng danh sách từ do chính use case chọn: sinh payload theo yêu cầu nhận được.
    class Echo(FakeGenerator):
        async def generate(self, request):  # type: ignore[no-untyped-def]
            self.requests.append(request)
            chosen = [w for w in words if w.term in {i.term for i in request.items}]
            return _llm_payload(chosen)

    env.generator = Echo()
    env.create = _rebuild(env, env.generator)
    detail = await env.create.execute(env.me, CreateQuizCommand())
    assert (detail.quiz.source, detail.quiz.note, detail.quiz.fallback_reason) == (QuizSource.LLM, None, None)
    assert all(q.origin is QuestionOrigin.LLM for q in detail.questions)
    # Chỉ gửi từ, pinyin, nghĩa (security.md): mục gửi đi không có trường nào khác.
    assert {i.__slots__ for i in env.generator.requests[0].items} == {
        ("term", "pinyin", "meaning", "hsk_level")
    }


def _rebuild(env: Env, generator: FakeGenerator, timeout: float = 0.5) -> CreateQuizUseCase:
    drafter = QuizDrafter(
        generator, FallbackQuestionBuilder(FakeDistractors(), FakeExamples(), env.rng), timeout
    )
    return CreateQuizUseCase(
        lambda: env.uow,
        FakeProfiles(),
        drafter,
        FakeRelated(),
        EstimateRetrievabilityUseCase(FsrsScheduler(enable_fuzzing=False)),
        LLM_ON,
        env.clock,
        env.rng,
    )


async def test_llm_invalid_then_valid_regenerates_once() -> None:
    """US-LLM-02: đề sai lược đồ được sinh lại đúng một lần."""
    words = _words()

    class Flaky(FakeGenerator):
        async def generate(self, request):  # type: ignore[no-untyped-def]
            self.requests.append(request)
            if len(self.requests) == 1:
                return {"questions": "hỏng"}
            return _llm_payload([w for w in words if w.term in {i.term for i in request.items}])

    env = Env(words, None, LLM_ON)
    gen = Flaky()
    env.create = _rebuild(env, gen)
    detail = await env.create.execute(env.me, CreateQuizCommand())
    assert len(gen.requests) == 2 and detail.quiz.source is QuizSource.LLM


async def test_llm_invalid_twice_falls_back_without_third_attempt() -> None:
    gen = FakeGenerator("rác", {"questions": []}, {"questions": []})
    env = Env(_words(), gen, LLM_ON)
    env.create = _rebuild(env, gen)
    detail = await env.create.execute(env.me, CreateQuizCommand())
    assert len(gen.requests) == 2
    assert detail.quiz.source is QuizSource.FALLBACK
    assert detail.quiz.fallback_reason is FallbackReason.INVALID_SCHEMA


async def test_llm_timeout_falls_back() -> None:
    """US-LLM-03: quá thời gian chờ → đề dự phòng."""
    gen = FakeGenerator({"questions": []}, delay=5.0)
    env = Env(_words(), gen, LLM_ON)
    env.create = _rebuild(env, gen, timeout=0.05)
    detail = await env.create.execute(env.me, CreateQuizCommand())
    assert detail.quiz.fallback_reason is FallbackReason.TIMEOUT
    assert detail.quiz.source is QuizSource.FALLBACK and len(detail.questions) == 10


async def test_llm_unavailable_and_unexpected_errors_fall_back() -> None:
    for error, reason in (
        (QuizGeneratorUnavailableError("network"), FallbackReason.NETWORK),
        (RuntimeError("lỗi lạ"), FallbackReason.NETWORK),
    ):
        gen = FakeGenerator(error)
        env = Env(_words(), gen, LLM_ON)
        env.create = _rebuild(env, gen)
        detail = await env.create.execute(env.me, CreateQuizCommand())
        assert detail.quiz.fallback_reason is reason and detail.quiz.source is QuizSource.FALLBACK


async def test_llm_missing_words_are_topped_up_with_fallback_questions() -> None:
    """F09.07 bước 5: bù câu dự phòng cho từ LLM bỏ sót → nguồn `mixed`, mỗi từ đúng một câu."""
    words = _words()

    class Partial(FakeGenerator):
        async def generate(self, request):  # type: ignore[no-untyped-def]
            self.requests.append(request)
            chosen = [w for w in words if w.term in {i.term for i in request.items}]
            return _llm_payload(chosen, skip={chosen[0].entry_id, chosen[1].entry_id})

    env = Env(words, None, LLM_ON)
    env.create = _rebuild(env, Partial())
    detail = await env.create.execute(env.me, CreateQuizCommand())
    origins = [q.origin for q in detail.questions]
    assert detail.quiz.source is QuizSource.MIXED
    assert origins.count(QuestionOrigin.FALLBACK) == 2 and origins.count(QuestionOrigin.LLM) == 8
    assert len({q.vocab_entry_id for q in detail.questions}) == 10


async def test_daily_llm_limit_uses_fallback_and_fallback_quizzes_do_not_count() -> None:
    """F13.05: chỉ đề không-dự-phòng tính vào hạn mức ngày; vượt hạn mức vẫn có bài (dự phòng)."""
    words = _words()

    class Echo(FakeGenerator):
        async def generate(self, request):  # type: ignore[no-untyped-def]
            self.requests.append(request)
            return _llm_payload([w for w in words if w.term in {i.term for i in request.items}])

    gen = Echo()
    env = Env(words, gen, LLM_ON)
    env.create = _rebuild(env, gen)
    first = await env.create.execute(env.me, CreateQuizCommand())
    second = await env.create.execute(env.me, CreateQuizCommand())
    third = await env.create.execute(env.me, CreateQuizCommand())
    assert [q.quiz.source for q in (first, second)] == [QuizSource.LLM, QuizSource.LLM]
    assert (
        third.quiz.source is QuizSource.FALLBACK and third.quiz.fallback_reason is FallbackReason.DAILY_LIMIT
    )
    assert len(gen.requests) == 2
    env.clock.at = NOW + timedelta(days=1)  # sang ngày mới thì được dùng LLM lại
    fourth = await env.create.execute(env.me, CreateQuizCommand())
    assert fourth.quiz.source is QuizSource.LLM


async def test_selection_prefers_low_retrievability_words() -> None:
    """US-NH-45 TC3: ưu tiên từ sắp quên; từ vừa ôn (R cao) chỉ chiếm phần nhỏ."""
    words = _words(30)
    env = Env(words)
    for w in words[:10]:  # 10 từ vừa ôn hôm qua với S lớn → R cao
        env.add_cards(w.entry_id)
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    high_r = {w.entry_id for w in words[:10]}
    picked_high = sum(1 for q in detail.questions if q.vocab_entry_id in high_r)
    assert picked_high <= 1


async def test_submit_grades_reschedules_wrong_words_once_and_blocks_second_submit() -> None:
    """US-NH-46..48: chấm ở máy chủ, từ sai đặt due = now, đã thuộc → đang học, nộp lần hai bị từ chối."""
    words = _words()
    env = Env(words)
    for w in words:
        env.add_cards(w.entry_id, due_in_days=9)
    env.uow.cards.items[1].is_suspended = True  # thẻ tạm ngưng của từ 1
    env.vocab.status[2] = "known"
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    quiz_id = detail.quiz.id
    questions = detail.questions
    answers = [AnswerInput(q.id, q.correct_answer) for q in questions]
    wrong = questions[0]
    answers[0] = AnswerInput(wrong.id, "chắc chắn sai")
    answers.pop()  # câu cuối chưa trả lời → sai
    unanswered = questions[-1]

    result = await env.submit.execute(env.me, quiz_id, answers)

    assert result.quiz.status is QuizStatus.SUBMITTED
    assert result.quiz.score == 8 and result.quiz.submitted_at == NOW
    assert result.quiz.wrong_cards_rescheduled_at == NOW
    by_id = {q.id: q for q in result.questions}
    assert by_id[wrong.id].is_correct is False and by_id[unanswered.id].user_answer is None
    wrong_entries = {wrong.vocab_entry_id, unanswered.vocab_entry_id}
    for card in env.uow.cards.items.values():
        if card.vocab_entry_id in wrong_entries:
            assert card.schedule.due_at == NOW and card.is_suspended is False
            assert card.schedule.stability is not None  # S giữ nguyên
        else:
            assert card.schedule.due_at == NOW + timedelta(days=9)
    assert set(result.rescheduled_terms) == {f"词{i}" for i in wrong_entries}
    assert env.uow.commits >= 2
    if 2 in wrong_entries:
        assert env.vocab.status[2] == "learning"

    with pytest.raises(QuizAlreadySubmittedError):
        await env.submit.execute(env.me, quiz_id, answers)
    reopened = await env.get.execute(env.me, quiz_id)
    assert reopened.rescheduled_terms == result.rescheduled_terms  # tải lại không tính lại


async def test_submit_skips_ignored_and_deleted_words_and_validates_answers() -> None:
    words = _words()
    env = Env(words)
    for w in words:
        env.add_cards(w.entry_id, due_in_days=9)
    detail = await env.create.execute(env.me, CreateQuizCommand(10))
    first, second = detail.questions[0], detail.questions[1]
    env.vocab.status[first.vocab_entry_id or 0] = "ignored"  # bị Bỏ qua sau khi ra đề
    env.vocab.removed.add(second.vocab_entry_id or 0)  # bị xóa sau khi ra đề
    with pytest.raises(InvalidQuizAnswersError):
        await env.submit.execute(env.me, detail.quiz.id, [AnswerInput(99999, "x")])
    with pytest.raises(InvalidQuizAnswersError):
        await env.submit.execute(
            env.me, detail.quiz.id, [AnswerInput(first.id, "a"), AnswerInput(first.id, "b")]
        )
    assert env.repo.quizzes[detail.quiz.id].status is QuizStatus.IN_PROGRESS
    result = await env.submit.execute(env.me, detail.quiz.id, [])  # nộp trắng: mọi câu sai
    assert result.quiz.score == 0
    ignored_cards = [c for c in env.uow.cards.items.values() if c.vocab_entry_id == first.vocab_entry_id]
    deleted_cards = [c for c in env.uow.cards.items.values() if c.vocab_entry_id == second.vocab_entry_id]
    assert all(c.schedule.due_at == NOW + timedelta(days=9) for c in ignored_cards + deleted_cards)
    assert first.vocab_entry_id is not None and f"词{first.vocab_entry_id}" not in result.rescheduled_terms


async def test_other_users_quiz_is_not_found_and_admin_delete_is_audited() -> None:
    """US-NH-46 TC5, US-NH-49 TC4, F13.07."""
    env = Env(_words())
    detail = await env.create.execute(env.me, CreateQuizCommand())
    stranger = identity(2)
    with pytest.raises(QuizNotFoundError):
        await env.get.execute(stranger, detail.quiz.id)
    with pytest.raises(QuizNotFoundError):
        await env.submit.execute(stranger, detail.quiz.id, [])
    with pytest.raises(PermissionDeniedError):
        await env.get.execute(stranger, detail.quiz.id, owner_id=1)
    page = await ListQuizzesUseCase(lambda: env.uow).execute(admin_identity(), 1, 20, owner_id=1)
    assert page.total == 1
    delete = DeleteQuizUseCase(lambda: env.uow, env.clock)
    await delete.execute(admin_identity(), detail.quiz.id, owner_id=1)
    assert env.repo.deleted == [detail.quiz.id]
    assert env.uow.audit.rows[0]["action"] == "quiz.delete" and env.uow.audit.rows[0]["target_user_id"] == 1
    with pytest.raises(QuizNotFoundError):
        await delete.execute(admin_identity(), detail.quiz.id, owner_id=1)
