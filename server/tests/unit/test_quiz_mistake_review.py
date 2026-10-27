"""M09 F09.10 (US-NH-79) — "Vì sao sai?": kiểm LLM, dự phòng, hạn mức riêng, không lộ đáp án.

LLM luôn được giả (FakeMistakeGenerator / httpx.MockTransport), không gọi Gemini thật.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.core.ai_policy import StaticAiPolicy
from app.core.single_flight import SingleFlight
from app.modules.quiz.api.mistake_schemas import MistakeReviewResponse
from app.modules.quiz.application.drafting import FallbackQuestionBuilder
from app.modules.quiz.application.mistake_practice import MistakePracticeBuilder
from app.modules.quiz.application.mistake_review_checker import MistakeReviewChecker
from app.modules.quiz.application.ports import MistakeReviewRequest
from app.modules.quiz.application.use_cases.answer_mistake_practice import AnswerMistakePracticeUseCase
from app.modules.quiz.application.use_cases.review_mistake import MistakeReviewConfig, ReviewMistakeUseCase
from app.modules.quiz.domain.entities import (
    ExampleRow,
    GradedAnswer,
    NewQuestion,
    NewQuiz,
    QuestionOrigin,
    QuestionType,
    QuizSource,
    QuizStatus,
    QuizWord,
)
from app.modules.quiz.domain.errors import (
    InvalidPracticeChoiceError,
    MistakePracticeNotFoundError,
    QuestionNotWrongError,
    QuizGeneratorUnavailableError,
    QuizNotFoundError,
    QuizNotSubmittedError,
    QuizQuestionNotFoundError,
)
from app.modules.quiz.infrastructure.gemini_mistake import (
    RESPONSE_SCHEMA,
    GeminiMistakeReviewGenerator,
    build_prompt,
)
from tests.conftest import FixedClock
from tests.unit.quiz_fakes import (
    FakeDistractors,
    FakeExamples,
    FakeProfiles,
    FakeQuizRepo,
    FakeQuizUow,
    FakeQuizVocab,
)
from tests.unit.review_fakes import identity

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
WORD = QuizWord(0, "学习", "xué xí", "học tập", 1, "")
EXPLANATION = "学习 (xué xí): học tập"


def _practice(answer: str = "học tập", prompt: str = "“学习” nghĩa là gì?") -> dict[str, Any]:
    return {
        "prompt": prompt,
        "options": ["học tập", "ăn cơm", "đi ngủ", "chạy bộ"],
        "answer": answer,
        "explanation": "学习 là học tập",
    }


def _payload(**practice: Any) -> dict[str, Any]:
    return {
        "explanation": "Bạn nhầm sang từ khác.",
        "difference": "学习 là học, 练习 là luyện tập.",
        "practice": {**_practice(), **practice},
    }


class FakeFacts:
    def __init__(self, word: QuizWord | None = WORD) -> None:
        self.word = word

    async def facts(self, term: str) -> QuizWord | None:
        return self.word


class FakeLevels:
    def __init__(self, level: int | None = 1) -> None:
        self.level = level

    async def difficulties(self, sentences: Sequence[str]) -> list[int | None]:
        return [self.level for _ in sentences]


class FakeMistakeGenerator:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.requests: list[MistakeReviewRequest] = []

    async def generate(self, request: MistakeReviewRequest) -> object:
        self.requests.append(request)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class Harness:
    def __init__(
        self,
        generator: FakeMistakeGenerator,
        *,
        enabled: bool = True,
        limit: int = 3,
        examples: FakeExamples | None = None,
        levels: FakeLevels | None = None,
        facts: FakeFacts | None = None,
    ) -> None:
        self.repo = FakeQuizRepo()
        self.uow = FakeQuizUow(FakeQuizVocab(), self.repo, examples=examples)
        self.generator = generator
        rng = random.Random(1)
        builder = FallbackQuestionBuilder(FakeDistractors(), examples or FakeExamples(), rng)
        self.review = ReviewMistakeUseCase(
            lambda: self.uow,  # type: ignore[arg-type,return-value]
            facts or FakeFacts(),
            FakeProfiles(2, "UTC"),
            generator,
            MistakeReviewChecker(levels or FakeLevels()),
            MistakePracticeBuilder(builder),
            StaticAiPolicy(enabled, limit),
            SingleFlight(),
            FixedClock(NOW),
            MistakeReviewConfig(20.0),
        )
        self.answer = AnswerMistakePracticeUseCase(lambda: self.uow)  # type: ignore[arg-type,return-value]
        self.quiz_id = 0
        self.question_ids: list[int] = []

    async def seed(self, *, submitted: bool = True, user_id: int = 1) -> None:
        quiz, rows = await self.repo.add(
            NewQuiz(user_id, QuizSource.LLM, 2, NOW),
            [
                NewQuestion(
                    QuestionType.MULTIPLE_CHOICE,
                    "“学习” nghĩa là gì?",
                    "học tập",
                    QuestionOrigin.LLM,
                    options=["học tập", "ăn cơm", "đi ngủ", "chạy bộ"],
                    explanation=EXPLANATION,
                    vocab_entry_id=1,
                    term="学习",
                )
                for _ in range(2)
            ],
        )
        self.quiz_id, self.question_ids = quiz.id, [q.id for q in rows]
        if submitted:
            quiz.status = QuizStatus.SUBMITTED
            await self.repo.save_result(
                quiz, [GradedAnswer(rows[0].id, "ăn cơm", False), GradedAnswer(rows[1].id, "học tập", True)]
            )

    async def run(self, index: int = 0, user_id: int = 1) -> Any:
        return await self.review.execute(identity(user_id), self.quiz_id, self.question_ids[index])


async def _ready(*results: object, **kwargs: Any) -> Harness:
    h = Harness(FakeMistakeGenerator(*results), **kwargs)
    await h.seed()
    return h


async def test_llm_review_is_validated_saved_and_reopened_without_calling_llm_again() -> None:
    h = await _ready(_payload())
    first = await h.run()
    assert first.review.origin is QuestionOrigin.LLM and not first.cached
    assert first.review.practice is not None and first.review.practice.answer == "học tập"
    second = await h.run()
    assert second.cached and second.review == first.review
    assert len(h.generator.requests) == 1  # US-NH-79 TC4: mở lại không gọi lại LLM
    assert h.uow.commits == 1


async def test_request_to_llm_has_only_word_data_and_the_two_options() -> None:
    h = await _ready(_payload())
    await h.run()
    (request,) = h.generator.requests
    assert request == MistakeReviewRequest("学习", "xué xí", "học tập", 1, "ăn cơm", "học tập", 2)


async def test_response_hides_practice_answer_until_the_learner_chooses() -> None:
    """US-NH-79 TC2: đáp án câu luyện chỉ trả sau khi chọn."""
    h = await _ready(_payload())
    body = MistakeReviewResponse.from_view(await h.run()).model_dump()
    assert set(body["practice"]) == {"prompt", "options"}
    assert body["ai_label"] == "Do AI viết, có thể chưa chính xác"
    assert "answer" not in json.dumps(body, ensure_ascii=False).replace("answer_", "")


@pytest.mark.parametrize(
    "bad",
    [
        _payload(answer="không có trong lựa chọn"),  # đáp án ngoài 4 lựa chọn
        _payload(options=["học tập", "học tập", "đi ngủ", "chạy bộ"]),  # lựa chọn trùng
        _payload(options=["học tập", "ăn cơm", "đi ngủ"]),  # thiếu lựa chọn
        _payload(prompt="Hôm nay trời đẹp?"),  # không chứa từ cần học
        _payload(answer="ăn cơm"),  # mâu thuẫn từ điển (nghĩa của 学习 là học tập)
        {"explanation": "x"},  # sai lược đồ
        "rác",
        None,
    ],
)
async def test_invalid_llm_content_is_discarded_and_fallback_is_saved(bad: object) -> None:
    """US-NH-79 TC5."""
    h = await _ready(bad)
    result = await h.run()
    assert result.review.origin is QuestionOrigin.FALLBACK
    assert result.review.explanation == EXPLANATION and result.review.difference is None


async def test_too_hard_practice_is_discarded() -> None:
    h = await _ready(_payload(prompt="“学习”很难"), levels=FakeLevels(6))
    assert (await h.run()).review.origin is QuestionOrigin.FALLBACK


@pytest.mark.parametrize(
    "error", [QuizGeneratorUnavailableError("timeout"), RuntimeError("lạ"), QuizGeneratorUnavailableError()]
)
async def test_llm_failure_uses_fallback_not_an_error(error: Exception) -> None:
    h = await _ready(error)
    result = await h.run()
    assert result.review.origin is QuestionOrigin.FALLBACK and result.review.explanation == EXPLANATION


async def test_llm_disabled_or_daily_limit_uses_fallback_without_calling_llm() -> None:
    disabled = await _ready(enabled=False)
    assert (await disabled.run()).review.origin is QuestionOrigin.FALLBACK
    assert disabled.generator.requests == []
    limited = await _ready(_payload(), limit=1)
    assert (await limited.run(0)).review.origin is QuestionOrigin.LLM  # dùng hết 1 lượt
    limited.repo.items[limited.quiz_id][1].is_correct = False  # câu thứ hai cũng sai
    again = await limited.run(1)
    assert again.review.origin is QuestionOrigin.FALLBACK and len(limited.generator.requests) == 1


async def test_fallback_practice_comes_from_dictionary_example_when_available() -> None:
    example = ExampleRow(5, "我每天学习汉语", "wǒ", "Mỗi ngày tôi học tiếng Trung", 1)
    examples = FakeExamples({"学习": [example]}, [f"bản dịch nhiễu {i}" for i in range(8)])
    h = await _ready(enabled=False, examples=examples)
    review = (await h.run()).review
    assert review.practice is not None and len(review.practice.options) == 4
    assert review.practice.answer in review.practice.options
    assert "我每天" in review.practice.prompt and "学习" in review.practice.options


async def test_fallback_without_example_shows_explanation_only() -> None:
    review = (await (await _ready(enabled=False)).run()).review
    assert review.practice is None and review.explanation == EXPLANATION


async def test_unknown_word_still_gets_an_explanation() -> None:
    """Từ không còn trong từ điển (hoặc đã xóa khỏi sổ tay) vẫn giải thích được từ trường explanation."""
    h = await _ready(enabled=False, facts=FakeFacts(None))
    assert (await h.run()).review.explanation == EXPLANATION


async def test_only_wrong_questions_of_submitted_own_quiz_are_allowed() -> None:
    h = await _ready()
    with pytest.raises(QuestionNotWrongError):
        await h.run(1)  # câu đúng
    with pytest.raises(QuizNotFoundError):
        await h.run(0, user_id=2)  # bài của người khác → 404
    with pytest.raises(QuizQuestionNotFoundError):
        await h.review.execute(identity(1), h.quiz_id, 999_999)
    open_quiz = Harness(FakeMistakeGenerator())
    await open_quiz.seed(submitted=False)
    with pytest.raises(QuizNotSubmittedError):
        await open_quiz.run()
    assert h.generator.requests == [] and open_quiz.generator.requests == []


async def test_answering_practice_grades_on_server_without_saving_anything() -> None:
    """US-NH-79 TC2: chấm ở máy chủ; không lưu, không đổi điểm bài."""
    h = await _ready(_payload())
    await h.run()
    quiz_before = h.repo.quizzes[h.quiz_id].score
    commits, saved = h.uow.commits, list(h.repo.items[h.quiz_id])
    wrong = await h.answer.execute(identity(1), h.quiz_id, h.question_ids[0], "ăn cơm")
    right = await h.answer.execute(identity(1), h.quiz_id, h.question_ids[0], " Học Tập ")
    assert (wrong.is_correct, wrong.correct_answer) == (False, "học tập")
    assert right.is_correct and right.explanation == "学习 là học tập"
    assert h.uow.commits == commits and h.repo.quizzes[h.quiz_id].score == quiz_before
    assert h.repo.items[h.quiz_id] == saved


async def test_answering_requires_existing_practice_and_a_listed_choice() -> None:
    h = await _ready(_payload())
    with pytest.raises(MistakePracticeNotFoundError):  # chưa bấm "Vì sao sai?"
        await h.answer.execute(identity(1), h.quiz_id, h.question_ids[0], "học tập")
    await h.run()
    with pytest.raises(InvalidPracticeChoiceError):
        await h.answer.execute(identity(1), h.quiz_id, h.question_ids[0], "chọn bừa")
    with pytest.raises(QuizNotFoundError):
        await h.answer.execute(identity(2), h.quiz_id, h.question_ids[0], "học tập")
    no_practice = await _ready(enabled=False)
    await no_practice.run()
    with pytest.raises(MistakePracticeNotFoundError):
        await no_practice.answer.execute(identity(1), no_practice.quiz_id, no_practice.question_ids[0], "x")


# --------------------------------------------------------------------------- adapter Gemini (HTTP giả)
SECRET = "AIza-SECRET-KEY-do-not-leak"


class Recorder:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def __call__(self, call: Any) -> None:
        self.calls.append(call)


def _gemini(response: httpx.Response, requests: list[httpx.Request], rec: Recorder) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response

    return GeminiMistakeReviewGenerator(
        SecretStr(SECRET), "gemini-test", 20.0, rec, transport=httpx.MockTransport(handler)
    )


async def test_gemini_adapter_sends_no_personal_data_and_key_only_in_header() -> None:
    text = json.dumps(_payload(), ensure_ascii=False)
    body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
    requests: list[httpx.Request] = []
    rec = Recorder()
    request = MistakeReviewRequest("学习", "xué xí", "học tập", 1, "ăn cơm", "học tập", 2)
    payload = await _gemini(httpx.Response(200, json=body), requests, rec).generate(request)
    assert isinstance(payload, dict) and payload["practice"]["answer"] == "học tập"
    sent = requests[0]
    assert SECRET not in str(sent.url) and sent.headers["x-goog-api-key"] == SECRET
    config = json.loads(sent.content)["generationConfig"]
    assert config["responseSchema"] == RESPONSE_SCHEMA
    prompt = json.loads(sent.content)["contents"][0]["parts"][0]["text"]
    assert "学习" in prompt and "ăn cơm" in prompt and "HSK 3 trở xuống" in prompt and "@" not in prompt
    assert [(c.operation, c.status) for c in rec.calls] == [("mistake_review", "ok")]


async def test_gemini_adapter_failure_maps_to_unavailable() -> None:
    request = MistakeReviewRequest("学习", None, None, None, None, "học tập")
    gen = _gemini(httpx.Response(403), [], Recorder())
    with pytest.raises(QuizGeneratorUnavailableError):
        await gen.generate(request)


def test_prompt_marks_blank_answer_and_unknown_level() -> None:
    prompt = build_prompt(MistakeReviewRequest("学习", None, None, None, None, "học tập"))
    assert "bỏ trống" in prompt and "chưa xác định" in prompt and "ngoài HSK" in prompt
