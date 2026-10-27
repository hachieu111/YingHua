"""M09 - adapter Gemini (F09.06) và rà soát đề LLM (F09.07). HTTP luôn mock, không gọi Gemini thật."""

from __future__ import annotations

import json
import logging
import random
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.quiz.api.dependencies import build_generator
from app.modules.quiz.application.drafting import FallbackQuestionBuilder, QuizDrafter
from app.modules.quiz.application.llm_review import LlmReviewer
from app.modules.quiz.application.ports import ExternalCall, GenerationItem, QuizGenerationRequest
from app.modules.quiz.domain.entities import ExampleRow, FallbackReason, QuizSource, QuizWord
from app.modules.quiz.domain.errors import QuizGeneratorUnavailableError
from app.modules.quiz.domain.llm_review import contradicts_dictionary, meaning_keywords
from app.modules.quiz.domain.llm_schema import validate_llm_payload
from app.modules.quiz.infrastructure.adapters import DisabledQuizGenerator
from app.modules.quiz.infrastructure.gemini import (
    API_KEY_HEADER,
    RESPONSE_SCHEMA,
    GeminiQuizGenerator,
    build_prompt,
)
from tests.unit.quiz_fakes import FakeDistractors, FakeExamples

SECRET = "AIza-SECRET-KEY-do-not-leak"
REQUEST = QuizGenerationRequest(
    [GenerationItem("学习", "xué xí", "học", 1), GenerationItem("朋友", "péng yǒu", "bạn bè", 2)],
    2,
    learner_level=2,
)


def _good_body() -> dict[str, Any]:
    questions = [
        {
            "term": "学习",
            "type": "multiple_choice",
            "prompt": "“学习” nghĩa là gì?",
            "options": ["học", "ăn", "ngủ", "chạy"],
            "answer": "học",
            "explanation": "học tập",
            "example_zh": "我每天学习汉语",
            "example_vi": "Mỗi ngày tôi học tiếng Trung",
        },
        {
            "term": "朋友",
            "type": "fill_blank",
            "prompt": "Điền: 他是我的＿＿",
            "answer": "朋友",
            "explanation": "bạn bè",
            "example_zh": "他是我的朋友",
            "example_vi": "Anh ấy là bạn tôi",
        },
    ]
    text = json.dumps({"questions": questions}, ensure_ascii=False)
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}


class RecordingLog:
    def __init__(self) -> None:
        self.calls: list[ExternalCall] = []

    async def record(self, call: ExternalCall) -> None:
        self.calls.append(call)


class Server:
    """Máy chủ Gemini giả: trả lần lượt các phản hồi/ngoại lệ đã định và ghi lại các yêu cầu nhận được."""

    def __init__(self, *outcomes: httpx.Response | Exception) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _generator(
    server: Server, log: RecordingLog | None = None, timeout: float = 20.0, sleeps: list[float] | None = None
) -> GeminiQuizGenerator:
    async def no_sleep(seconds: float) -> None:
        if sleeps is not None:
            sleeps.append(seconds)

    return GeminiQuizGenerator(
        SecretStr(SECRET),
        "gemini-flash-latest",
        timeout,
        log or RecordingLog(),
        transport=httpx.MockTransport(server),
        sleep=no_sleep,
    )


def _ok(body: dict[str, Any] | None = None) -> httpx.Response:
    return httpx.Response(200, json=body or _good_body())


async def test_success_sends_key_in_header_only_and_no_personal_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    server, log = Server(_ok()), RecordingLog()
    caplog.set_level(logging.DEBUG)
    payload = await _generator(server, log).generate(REQUEST)

    assert isinstance(payload, dict) and len(payload["questions"]) == 2
    request = server.requests[0]
    assert str(request.url).endswith("/v1beta/models/gemini-flash-latest:generateContent")
    assert request.url.query == b"" and SECRET not in str(request.url)
    assert request.headers[API_KEY_HEADER] == SECRET
    body = json.loads(request.content)
    config = body["generationConfig"]
    assert config["responseMimeType"] == "application/json" and config["responseSchema"] == RESPONSE_SCHEMA
    assert config["thinkingConfig"] == {"thinkingLevel": "low"}
    assert config["temperature"] == pytest.approx(0.7)
    prompt = body["contents"][0]["parts"][0]["text"]
    assert "学习" in prompt and "péng yǒu" in prompt and "HSK 2" in prompt and "HSK 3 trở xuống" in prompt
    assert "example_zh" in RESPONSE_SCHEMA["properties"]["questions"]["items"]["properties"]
    assert SECRET not in prompt and "@" not in prompt
    assert [(c.provider, c.operation, c.status, c.error_code) for c in log.calls] == [
        ("gemini", "generate_quiz", "ok", None)
    ]
    assert all(SECRET not in record.getMessage() for record in caplog.records)
    assert SECRET not in repr(log.calls)


async def test_prompt_marks_unknown_level() -> None:
    prompt = build_prompt(QuizGenerationRequest([GenerationItem("学习", None, None)], 1, None))
    assert "chưa xác định" in prompt and "ngoài HSK" in prompt and "HSK 1-3" in prompt


async def test_payload_passes_schema_validation() -> None:
    payload = await _generator(Server(_ok())).generate(REQUEST)
    words = [
        QuizWord(1, "学习", "xué xí", "học", 1, "learning"),
        QuizWord(2, "朋友", None, "bạn bè", 2, "known"),
    ]
    validated = validate_llm_payload(payload, words)
    assert validated is not None and len(validated.questions) == 2
    assert validated.examples[1].zh == "我每天学习汉语" and validated.examples[2].vi == "Anh ấy là bạn tôi"


async def test_retry_once_on_429_with_backoff_then_success() -> None:
    server, log, sleeps = Server(httpx.Response(429), _ok()), RecordingLog(), []
    payload = await _generator(server, log, sleeps=sleeps).generate(REQUEST)
    assert isinstance(payload, dict) and len(server.requests) == 2 and len(sleeps) == 1
    assert [(c.status, c.error_code) for c in log.calls] == [("error", "HTTP_429"), ("ok", None)]


@pytest.mark.parametrize("status", [429, 503, 500])
async def test_repeated_server_errors_raise_unavailable(status: int) -> None:
    server, log = Server(httpx.Response(status), httpx.Response(status)), RecordingLog()
    with pytest.raises(QuizGeneratorUnavailableError) as exc:
        await _generator(server, log).generate(REQUEST)
    assert exc.value.reason == FallbackReason.NETWORK.value and len(server.requests) == 2
    assert [c.error_code for c in log.calls] == [f"HTTP_{status}"] * 2


async def test_client_error_is_not_retried() -> None:
    server = Server(httpx.Response(403, json={"error": {"message": "key sai"}}))
    with pytest.raises(QuizGeneratorUnavailableError):
        await _generator(server).generate(REQUEST)
    assert len(server.requests) == 1


async def test_no_retry_when_time_budget_is_exhausted() -> None:
    server = Server(httpx.Response(503), _ok())
    with pytest.raises(QuizGeneratorUnavailableError):
        await _generator(server, timeout=0.5).generate(REQUEST)  # ngân sách < thời gian chờ backoff
    assert len(server.requests) == 1


async def test_timeout_maps_to_timeout_reason_and_is_logged() -> None:
    server, log = Server(httpx.ReadTimeout("chậm")), RecordingLog()
    with pytest.raises(QuizGeneratorUnavailableError) as exc:
        await _generator(server, log).generate(REQUEST)
    assert exc.value.reason == FallbackReason.TIMEOUT.value
    assert [(c.status, c.error_code) for c in log.calls] == [("timeout", "TIMEOUT")]


async def test_network_error_maps_to_unavailable() -> None:
    server, log = Server(httpx.ConnectError("mất mạng")), RecordingLog()
    with pytest.raises(QuizGeneratorUnavailableError) as exc:
        await _generator(server, log).generate(REQUEST)
    assert exc.value.reason == FallbackReason.NETWORK.value and log.calls[0].error_code == "NETWORK"


async def test_thinking_config_rejected_then_dropped_on_retry() -> None:
    server = Server(httpx.Response(400, json={"error": {"message": "thinkingConfig không hỗ trợ"}}), _ok())
    payload = await _generator(server).generate(REQUEST)
    assert isinstance(payload, dict)
    first, second = (json.loads(r.content)["generationConfig"] for r in server.requests)
    assert "thinkingConfig" in first and "thinkingConfig" not in second


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="không phải json"),
        httpx.Response(
            200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{hỏng"}]}}]}
        ),
        httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}),
        httpx.Response(
            200, json={"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{}"}]}}]}
        ),
        httpx.Response(200, json={"candidates": []}),
    ],
)
async def test_blocked_truncated_or_broken_json_is_treated_as_invalid_schema(
    response: httpx.Response,
) -> None:
    log = RecordingLog()
    assert await _generator(Server(response), log).generate(REQUEST) is None
    assert [c.status for c in log.calls] == ["invalid"]


# --------------------------------------------------------------------------- rà soát F09.07
def test_meaning_keywords_ignore_stopwords_and_short_words() -> None:
    assert meaning_keywords("① là sự học tập; ăn") == {"học", "tập", "ăn"}


def _question(answer: str, qtype: str = "multiple_choice", term: str = "朋友") -> Any:
    payload = {
        "questions": [
            {
                "term": term,
                "type": qtype,
                "prompt": "câu hỏi",
                "options": ["a", answer] if qtype == "multiple_choice" else [],
                "answer": answer,
                "explanation": "x",
            }
        ]
    }
    words = [QuizWord(1, term, "pin", "bạn bè; người bạn", 2, "learning")]
    validated = validate_llm_payload(payload, words)
    assert validated is not None
    return validated.questions[0], words[0]


def test_contradiction_check_requires_shared_keyword_or_exact_term() -> None:
    assert not contradicts_dictionary(*_question("người bạn thân"))  # chung từ khóa "bạn"
    assert contradicts_dictionary(*_question("con mèo"))
    assert not contradicts_dictionary(*_question("朋友"))  # đáp án chữ Hán đúng bằng term
    assert contradicts_dictionary(*_question("同学"))
    assert not contradicts_dictionary(*_question("朋友", "fill_blank"))
    assert contradicts_dictionary(*_question("同学", "fill_blank"))
    no_meaning = QuizWord(1, "朋友", None, None, 2, "learning")
    question, _ = _question("con mèo")
    assert not contradicts_dictionary(question, no_meaning)  # không có nghĩa để đối chiếu


class FixedLevels:
    def __init__(self, *levels: int | None) -> None:
        self.levels = list(levels)

    async def difficulties(self, sentences: Any) -> list[int | None]:
        return [self.levels.pop(0) for _ in sentences]


async def _drafted(levels: FixedLevels, tatoeba: FakeExamples, body: dict[str, Any] | None = None) -> Any:
    words = [
        QuizWord(1, "学习", "xué xí", "học", 1, "learning"),
        QuizWord(2, "朋友", "péng yǒu", "bạn bè", 2, "known"),
    ]
    rng = random.Random(1)
    builder = FallbackQuestionBuilder(FakeDistractors(), tatoeba, rng)
    reviewer = LlmReviewer(levels, tatoeba, rng)
    payload = await _generator(Server(_ok(body))).generate(REQUEST)
    validated = validate_llm_payload(payload, words)
    assert validated is not None
    return await reviewer.review(validated, words, 2, set()), builder


async def test_reviewer_keeps_llm_example_only_if_easy_enough_else_uses_tatoeba() -> None:
    """F09.09: câu ví dụ LLM qua kiểm độ khó thì giữ; không qua thì thay bằng câu Tatoeba."""
    tatoeba = FakeExamples(
        {"朋友": [ExampleRow(77, "我有很多朋友", "py", "Tôi có nhiều bạn", 2)]}, ["dịch nhiễu"] * 5
    )
    questions, _ = await _drafted(
        FixedLevels(2, 5, 2), tatoeba
    )  # 学习: câu dễ (2 ≤ 3); 朋友: câu quá khó (5 > 3)
    first, second = questions
    assert "Ví dụ: 我每天学习汉语 — Mỗi ngày tôi học tiếng Trung" in (first.explanation or "")
    assert first.example_id is None
    assert second.example_id == 77 and "Ví dụ" not in (second.explanation or "")


async def test_reviewer_rejects_example_missing_the_term() -> None:
    body = _good_body()
    text = json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
    text["questions"][0]["example_zh"] = "我喜欢读书"  # không chứa 学习
    body["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(text, ensure_ascii=False)
    questions, _ = await _drafted(FixedLevels(1, 1, 1), FakeExamples(), body)
    assert "Ví dụ" not in (questions[0].explanation or "") and "Ví dụ" in (questions[1].explanation or "")


async def test_drafter_end_to_end_with_gemini_mock_builds_llm_quiz() -> None:
    words = [
        QuizWord(1, "学习", "xué xí", "học", 1, "learning"),
        QuizWord(2, "朋友", "péng yǒu", "bạn bè", 2, "known"),
    ]
    tatoeba, rng = FakeExamples(), random.Random(2)
    drafter = QuizDrafter(
        _generator(Server(_ok())),
        FallbackQuestionBuilder(FakeDistractors(), tatoeba, rng),
        20,
        LlmReviewer(FixedLevels(1, 1, 1), tatoeba, rng),
    )
    from app.modules.quiz.application.drafting import DraftInput

    drafted = await drafter.draft(DraftInput(words, words, {}, 2, None, learner_level=2))
    assert drafted.source is QuizSource.LLM and drafted.fallback_reason is None
    assert [q.vocab_entry_id for q in drafted.questions] == [1, 2]


async def test_drafter_falls_back_when_gemini_is_down() -> None:
    from app.modules.quiz.application.drafting import DraftInput

    words = [QuizWord(i, f"词{i}", "p", f"nghĩa {i}", 2, "learning") for i in range(1, 6)]
    tatoeba, rng = FakeExamples(), random.Random(2)
    drafter = QuizDrafter(
        _generator(Server(httpx.Response(503), httpx.Response(503))),
        FallbackQuestionBuilder(FakeDistractors(), tatoeba, rng),
        20,
    )
    drafted = await drafter.draft(DraftInput(words, words, {}, 2, None))
    assert drafted.source is QuizSource.FALLBACK and drafted.fallback_reason is FallbackReason.NETWORK


# --------------------------------------------------------------------------- lắp ghép
@pytest.mark.parametrize(
    ("enabled", "key", "provider", "expected"),
    [
        (True, SecretStr(SECRET), "gemini", GeminiQuizGenerator),
        (False, SecretStr(SECRET), "gemini", GeminiQuizGenerator),  # công tắc do use case kiểm (F13.05)
        (True, None, "gemini", DisabledQuizGenerator),
        (True, SecretStr(""), "gemini", DisabledQuizGenerator),
        (True, SecretStr(SECRET), "openai", DisabledQuizGenerator),
    ],
)
def test_container_picks_adapter_by_settings(
    enabled: bool, key: SecretStr | None, provider: str, expected: type
) -> None:
    class Stub:
        pass

    container: Any = Stub()
    container.settings = Settings.model_construct(
        llm_enabled=enabled,
        llm_api_key=key,
        llm_provider=provider,
        llm_model="gemini-flash-latest",
        llm_timeout_seconds=20.0,
    )
    container.session_factory = None
    assert isinstance(build_generator(container), expected)
    assert SECRET not in repr(container.settings.llm_api_key)  # SecretStr che khóa khi in
