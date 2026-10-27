"""M05 F05.09 (US-NH-78) — phân tích ngữ pháp câu thoại: kiểm kết quả LLM, cache, hạn mức.

LLM luôn được giả (FakeAnalyzer / httpx.MockTransport), không gọi Gemini thật.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.core.ai_policy import StaticAiPolicy
from app.core.single_flight import SingleFlight
from app.modules.auth.application.public import Identity
from app.modules.imaging.domain.entities import Bubble
from app.modules.reader.application.ports import GrammarRequest
from app.modules.reader.application.use_cases.analyze_grammar import AnalyzeGrammarUseCase, GrammarConfig
from app.modules.reader.domain.errors import (
    BubbleHasNoHanError,
    BubbleNotFoundError,
    GrammarAnalyzerUnavailableError,
    SentenceTooLongError,
)
from app.modules.reader.domain.grammar import (
    GrammarAnalysis,
    GrammarContent,
    GrammarStatus,
    content_from_json,
    content_to_json,
    example_has_pattern,
    normalize_sentence,
    parse_points,
    parse_tree,
    sentence_hash,
)
from app.modules.reader.infrastructure.gemini_grammar import (
    RESPONSE_SCHEMA,
    GeminiGrammarAnalyzer,
    build_prompt,
)
from tests.conftest import FixedClock
from tests.unit.review_fakes import identity

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
SENTENCE = "我把书放在桌子上。"


def _node(label: str, text: str, *children: dict[str, Any]) -> dict[str, Any]:
    return {"label": label, "text": text, "note": "ghi chú", "children": list(children)}


def _good_payload() -> dict[str, Any]:
    return {
        "tree": [
            _node("subject", "我"),
            _node("adverbial", "把书", _node("preposition", "把"), _node("object", "书")),
            _node("predicate", "放在桌子上。"),
        ],
        "points": [
            {
                "pattern": "把 + 宾语 + 动词",
                "name": "Câu chữ 把",
                "explanation": "Đưa tân ngữ lên trước động từ.",
                "example_zh": "他把门打开了",
                "example_vi": "Anh ấy mở cửa ra rồi",
            }
        ],
    }


# --------------------------------------------------------------------------- domain
def test_normalize_sentence_applies_nfc_and_collapses_whitespace_and_hash_is_stable() -> None:
    assert normalize_sentence("  我 \n 爱\t你  ") == "我 爱 你"
    assert sentence_hash("我爱你") == sentence_hash("我爱你") and len(sentence_hash("我爱你")) == 64
    assert sentence_hash("我爱你") != sentence_hash("我爱他")


def test_tree_leaves_must_rebuild_the_sentence_ignoring_punctuation() -> None:
    tree = parse_tree(_good_payload()["tree"], SENTENCE)
    assert [n.label for n in tree] == ["subject", "adverbial", "predicate"]
    assert tree[1].children[0].text == "把"


def test_tree_dropped_when_leaves_do_not_match_sentence() -> None:
    changed = _good_payload()["tree"]
    changed[0] = _node("subject", "你")  # đổi chữ
    assert parse_tree(changed, SENTENCE) == ()
    assert parse_tree(_good_payload()["tree"][:2], SENTENCE) == ()  # thiếu đoạn cuối


def test_tree_dropped_for_unknown_label_or_inconsistent_parent_or_bad_shape() -> None:
    bad_label = _good_payload()["tree"]
    bad_label[0]["label"] = "noun"
    assert parse_tree(bad_label, SENTENCE) == ()
    parent_mismatch = _good_payload()["tree"]
    parent_mismatch[1]["text"] = "把桌"  # nút cha không bằng phần ghép của các con
    assert parse_tree(parent_mismatch, SENTENCE) == ()
    assert parse_tree("không phải mảng", SENTENCE) == ()
    assert parse_tree([], SENTENCE) == ()
    assert parse_tree([{"label": "subject", "text": ""}], SENTENCE) == ()


def test_example_must_contain_every_han_fragment_of_pattern_in_order() -> None:
    assert example_has_pattern("不但……而且……", "他不但聪明而且努力")
    assert not example_has_pattern("不但……而且……", "他而且聪明不但努力")  # sai thứ tự
    assert example_has_pattern("把 + 宾语 + 动词", "他把门打开了")
    assert not example_has_pattern("把 + 宾语 + 动词", "他开门了")
    assert example_has_pattern(
        "把 + 宾语 + 动词 + 在/到 + 处所", "请把 手机 放在 桌子 上。"
    )  # lựa chọn / và dấu cách
    assert not example_has_pattern("S + V + O", "他开门了")  # không có chữ Hán nào để đối chiếu


def test_invalid_points_are_dropped_and_valid_ones_kept_up_to_three() -> None:
    good = _good_payload()["points"][0]
    wrong_example = {**good, "pattern": "比", "example_zh": "他很高"}
    placeholder = {**good, "example_zh": "请把N_A放在桌子上"}  # ký hiệu giữ chỗ còn sót
    missing_field = {k: v for k, v in good.items() if k != "example_vi"}
    kept = parse_points([wrong_example, placeholder, missing_field, "rác", good, dict(good)])
    assert [p.pattern for p in kept] == ["把 + 宾语 + 动词"]  # trùng cấu trúc chỉ giữ một
    many = [{**good, "pattern": f"把{i}", "example_zh": f"他把{i}门"} for i in range(5)]
    assert len(parse_points(many)) == 3


def test_content_round_trips_through_json() -> None:
    tree = parse_tree(_good_payload()["tree"], SENTENCE)
    content = GrammarContent(tree, tuple(parse_points(_good_payload()["points"])))
    assert content_from_json(content_to_json(content)) == content
    assert content_from_json({"tree": [{"label": "x"}]}) is None
    assert content_from_json("hỏng") is None


# --------------------------------------------------------------------------- use case
class FakeGrammarRepo:
    def __init__(self) -> None:
        self.analyses: dict[str, GrammarAnalysis] = {}
        self.requests: list[tuple[int, int | None, datetime]] = []

    async def get_by_hash(self, sentence_hash: str) -> GrammarAnalysis | None:
        return self.analyses.get(sentence_hash)

    async def add(
        self, sentence_hash: str, sentence: str, content: GrammarContent, model: str | None
    ) -> GrammarAnalysis:
        analysis = GrammarAnalysis(len(self.analyses) + 1, sentence, content, model)
        self.analyses[sentence_hash] = analysis
        return analysis

    async def add_request(self, user_id: int, analysis_id: int | None, requested_at: datetime) -> None:
        self.requests.append((user_id, analysis_id, requested_at))

    async def count_requests_between(self, user_id: int, start: datetime, end: datetime) -> int:
        return sum(1 for u, _, at in self.requests if u == user_id and start <= at < end)


class FakeBubbles:
    def __init__(self, bubble: Bubble) -> None:
        self._bubble = bubble

    async def get(self, bubble_id: int) -> Bubble | None:
        return self._bubble if bubble_id == self._bubble.id else None


class FakeReaderUow:
    def __init__(self, bubble: Bubble, grammar: FakeGrammarRepo) -> None:
        self.bubbles = FakeBubbles(bubble)
        self.grammar = grammar
        self.commits = 0

    async def __aenter__(self) -> FakeReaderUow:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakePages:
    def __init__(self, readable: bool = True) -> None:
        self.readable = readable

    async def can_read_translation(self, identity: Identity | None, translation_id: int) -> bool:
        return self.readable


class FakeAnalyzer:
    """Trả lần lượt các kết quả định sẵn; Exception thì ném ra."""

    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.requests: list[GrammarRequest] = []

    async def analyze(self, request: GrammarRequest) -> object:
        self.requests.append(request)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeLevels:
    def __init__(self, level: int | None = 2) -> None:
        self.level = level

    async def difficulties(self, sentences: Sequence[str]) -> list[int | None]:
        return [self.level for _ in sentences]


class FakeTimezones:
    async def timezone_of(self, user_id: int) -> str | None:
        return "UTC"


def _bubble(text: str = SENTENCE, text_vi: str | None = "Tôi để sách trên bàn") -> Bubble:
    return Bubble(
        id=1, translation_id=10, idx=0, class_name="speech_bubble", x=0, y=0, w=5, h=5, text_zh=text,
        text_vi=text_vi,
    )  # fmt: skip


class Harness:
    def __init__(
        self,
        analyzer: FakeAnalyzer,
        *,
        bubble: Bubble | None = None,
        enabled: bool = True,
        limit: int = 2,
        readable: bool = True,
        levels: FakeLevels | None = None,
    ) -> None:
        self.repo = FakeGrammarRepo()
        self.analyzer = analyzer
        self.uow = FakeReaderUow(bubble or _bubble(), self.repo)
        self.clock = FixedClock(NOW)
        self.use_case = AnalyzeGrammarUseCase(
            lambda: self.uow,  # type: ignore[arg-type,return-value]
            FakePages(readable),  # type: ignore[arg-type]
            analyzer,
            levels or FakeLevels(),
            FakeTimezones(),
            StaticAiPolicy(enabled, limit),
            SingleFlight(),
            self.clock,
            GrammarConfig(20.0, "gemini-test"),
        )

    async def run(self, user_id: int = 1) -> Any:
        return await self.use_case.execute(identity(user_id), 1)


async def test_analysis_keeps_valid_parts_saves_shared_cache_and_counts_one_request() -> None:
    h = Harness(FakeAnalyzer(_good_payload()))
    view = await h.run()
    assert view.status is GrammarStatus.OK and not view.cached
    assert view.content is not None and len(view.content.tree) == 3 and len(view.content.points) == 1
    assert [(u, a is not None) for u, a, _ in h.repo.requests] == [(1, True)]
    assert h.repo.analyses[sentence_hash(SENTENCE)].model == "gemini-test"


async def test_cache_hit_returns_immediately_without_llm_or_quota_even_for_another_user() -> None:
    """US-NH-78 TC6: câu đã phân tích (bởi ai cũng được) → không gọi LLM, không tốn hạn mức."""
    h = Harness(FakeAnalyzer(_good_payload()), limit=1)
    await h.run(user_id=1)
    again = await h.run(user_id=2)
    assert again.status is GrammarStatus.OK and again.cached
    assert len(h.analyzer.requests) == 1 and len(h.repo.requests) == 1
    # Cache vẫn dùng được khi người dùng đã hết hạn mức hoặc LLM bị tắt.
    exhausted = await h.run(user_id=1)
    assert exhausted.status is GrammarStatus.OK and exhausted.cached


async def test_cache_key_ignores_whitespace_differences() -> None:
    h = Harness(FakeAnalyzer(_good_payload()), bubble=_bubble(" 我把书放在桌子上。 \n"))
    await h.run()
    assert sentence_hash(SENTENCE) in h.repo.analyses


async def test_daily_limit_reached_blocks_new_sentences_only() -> None:
    h = Harness(FakeAnalyzer(_good_payload()), limit=0)
    view = await h.run()
    assert view.status is GrammarStatus.LIMIT_REACHED and view.content is None
    assert h.analyzer.requests == [] and h.repo.requests == []


async def test_limit_counts_only_today_requests_of_the_same_user() -> None:
    h = Harness(FakeAnalyzer(_good_payload()), limit=1)
    h.repo.requests.append((1, None, NOW - timedelta(days=1)))  # hôm qua không tính
    h.repo.requests.append((2, None, NOW))  # người khác không tính
    assert (await h.run()).status is GrammarStatus.OK
    h.repo.analyses.clear()
    h.analyzer.results.append(_good_payload())
    assert (await h.run()).status is GrammarStatus.LIMIT_REACHED  # lượt vừa rồi đã dùng hết hạn mức 1


async def test_llm_disabled_gives_unavailable_without_calling_or_counting() -> None:
    h = Harness(FakeAnalyzer(), enabled=False)
    view = await h.run()
    assert view.status is GrammarStatus.UNAVAILABLE and h.repo.requests == []


@pytest.mark.parametrize(
    "error", [GrammarAnalyzerUnavailableError("network"), asyncio.TimeoutError(), RuntimeError("lạ")]
)
async def test_llm_failure_gives_unavailable_and_nothing_cached_and_no_quota_used(error: Exception) -> None:
    """F05.09: lỗi kỹ thuật của LLM không làm người học mất lượt."""
    h = Harness(FakeAnalyzer(error))
    view = await h.run()
    assert view.status is GrammarStatus.UNAVAILABLE and h.repo.analyses == {}
    assert h.repo.requests == []


async def test_invalid_tree_is_dropped_but_valid_points_are_kept() -> None:
    payload = _good_payload()
    payload["tree"][0]["text"] = "你"
    view = await Harness(FakeAnalyzer(payload)).run()
    assert view.status is GrammarStatus.OK and view.content is not None
    assert view.content.tree == () and len(view.content.points) == 1


async def test_nothing_valid_gives_unanalyzable_and_is_not_cached() -> None:
    """US-NH-78 TC5: không còn phần nào hợp lệ → không cache kết quả rỗng; lượt gọi vẫn ghi."""
    payload = _good_payload()
    payload["tree"][0]["label"] = "noun"
    payload["points"][0]["example_zh"] = "他开门了"
    h = Harness(FakeAnalyzer(payload))
    view = await h.run()
    assert view.status is GrammarStatus.UNANALYZABLE and view.content is None
    assert h.repo.analyses == {} and [(u, a) for u, a, _ in h.repo.requests] == [(1, None)]
    assert (await Harness(FakeAnalyzer(None)).run()).status is GrammarStatus.UNANALYZABLE
    assert (await Harness(FakeAnalyzer(["rác"])).run()).status is GrammarStatus.UNANALYZABLE


async def test_example_too_hard_or_unmeasurable_is_dropped() -> None:
    hard = await Harness(FakeAnalyzer(_good_payload()), levels=FakeLevels(6)).run()
    assert hard.content is not None and hard.content.points == ()  # cây vẫn còn
    none = await Harness(FakeAnalyzer(_good_payload()), levels=FakeLevels(None)).run()
    assert none.content is not None and none.content.points == ()


async def test_unreadable_bubble_is_404_and_text_without_han_is_rejected() -> None:
    with pytest.raises(BubbleNotFoundError):
        await Harness(FakeAnalyzer(), readable=False).run()
    with pytest.raises(BubbleHasNoHanError):
        await Harness(FakeAnalyzer(), bubble=_bubble("123 ???")).run()
    with pytest.raises(SentenceTooLongError):
        await Harness(FakeAnalyzer(), bubble=_bubble("我" * 201)).run()


async def test_only_shared_machine_translation_is_sent_to_llm() -> None:
    h = Harness(FakeAnalyzer(_good_payload()))
    await h.run(user_id=77)
    (request,) = h.analyzer.requests
    assert request == GrammarRequest(SENTENCE, "Tôi để sách trên bàn")


# --------------------------------------------------------------------------- adapter Gemini (HTTP giả)
SECRET = "AIza-SECRET-KEY-do-not-leak"


class Recorder:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def __call__(self, call: Any) -> None:
        self.calls.append(call)


def _gemini(responses: list[httpx.Response], requests: list[httpx.Request], rec: Recorder) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return responses.pop(0)

    async def no_sleep(_: float) -> None:
        return None

    return GeminiGrammarAnalyzer(
        SecretStr(SECRET), "gemini-test", 20.0, rec, transport=httpx.MockTransport(handler), sleep=no_sleep
    )


def _ok_body(payload: dict[str, Any]) -> httpx.Response:
    text = json.dumps(payload, ensure_ascii=False)
    return httpx.Response(
        200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}
    )


async def test_gemini_adapter_sends_only_sentence_and_translation_with_key_in_header() -> None:
    requests: list[httpx.Request] = []
    rec = Recorder()
    analyzer = _gemini([_ok_body(_good_payload())], requests, rec)
    payload = await analyzer.analyze(GrammarRequest(SENTENCE, "Tôi để sách trên bàn"))
    assert isinstance(payload, dict) and len(payload["tree"]) == 3
    request = requests[0]
    assert SECRET not in str(request.url) and request.headers["x-goog-api-key"] == SECRET
    body = json.loads(request.content)
    prompt = body["contents"][0]["parts"][0]["text"]
    assert SENTENCE in prompt and "Tôi để sách trên bàn" in prompt and "@" not in prompt
    assert body["generationConfig"]["responseSchema"] == RESPONSE_SCHEMA
    assert [(c.operation, c.status) for c in rec.calls] == [("grammar", "ok")]


async def test_gemini_adapter_maps_http_errors_and_broken_json() -> None:
    rec = Recorder()
    down = _gemini([httpx.Response(503), httpx.Response(503)], [], rec)
    with pytest.raises(GrammarAnalyzerUnavailableError):
        await down.analyze(GrammarRequest(SENTENCE))
    broken = _gemini([httpx.Response(200, text="không phải json")], [], rec)
    assert await broken.analyze(GrammarRequest(SENTENCE)) is None


def test_prompt_lists_allowed_labels_and_omits_translation_when_missing() -> None:
    prompt = build_prompt(GrammarRequest(SENTENCE))
    assert "subject" in prompt and "Bản dịch tham khảo" not in prompt
