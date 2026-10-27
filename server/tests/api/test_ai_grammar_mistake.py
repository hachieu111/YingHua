"""F05.09 (US-NH-78) và F09.10 (US-NH-79) qua API thật trên CSDL kiểm thử; LLM luôn được giả."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from app.core.ai_policy import StaticAiPolicy
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.reader.api.dependencies import build_reader_services, get_reader_services
from app.modules.reader.application.use_cases.analyze_grammar import AnalyzeGrammarUseCase, GrammarConfig
from app.modules.reader.domain.grammar import sentence_hash
from app.modules.reader.infrastructure.uow import SqlReaderUnitOfWork
from tests.api.test_imaging_reader import _drain, _worker
from tests.api.test_vocab_review import _ready_page
from tests.helpers import Account, error_code, make_admin, register
from tests.unit.test_grammar_analysis import SENTENCE, FakeAnalyzer, FakeLevels, FakeTimezones, _good_payload

pytestmark = pytest.mark.integration

API = "/api/v1"
QUIZZES = f"{API}/quizzes"
TERMS = list("一二三四五六七八九十百千")


async def _set_bubble_text(app: FastAPI, bubble_id: int, text_zh: str) -> None:
    async with app.state.container.session_factory() as session:
        await session.execute(
            text("UPDATE bubbles SET text_zh = :t WHERE id = :b"), {"t": text_zh, "b": bubble_id}
        )
        await session.execute(
            text("DELETE FROM grammar_analyses WHERE sentence_hash = :h"), {"h": sentence_hash(text_zh)}
        )
        await session.commit()


async def _scalar(app: FastAPI, sql: str, **params: Any) -> Any:
    async with app.state.container.session_factory() as session:
        return await session.scalar(text(sql), params)


@pytest.fixture
def grammar_llm(app: FastAPI) -> Iterator[dict[str, Any]]:
    """Thay use case phân tích ngữ pháp bằng bản dùng LLM giả; chỉnh `state['analyzer']`, `state['limit']`."""
    state: dict[str, Any] = {"analyzer": FakeAnalyzer(_good_payload()), "limit": 1}

    def override() -> Any:
        container = app.state.container
        services = build_reader_services(container)
        services.analyze_grammar = AnalyzeGrammarUseCase(
            lambda: SqlReaderUnitOfWork(container.session_factory),
            LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), container.clock),
            state["analyzer"],
            FakeLevels(2),
            FakeTimezones(),
            StaticAiPolicy(True, state["limit"]),
            container.single_flight,
            container.clock,
            GrammarConfig(20.0, "gemini-test"),
        )
        return services

    app.dependency_overrides[get_reader_services] = override
    yield state
    app.dependency_overrides.pop(get_reader_services, None)


async def test_grammar_llm_off_by_default_gives_gentle_unavailable_status(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner = await register(client)
    await _drain(_worker(app))
    _, bubbles = await _ready_page(client, app, owner)
    await _set_bubble_text(app, bubbles[0]["id"], SENTENCE)
    res = await client.post(f"{API}/bubbles/{bubbles[0]['id']}/grammar", headers=owner.headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["status"], body["tree"], body["points"], body["cached"]) == ("unavailable", [], [], False)
    assert body["message"] == "Tạm thời chưa phân tích được câu này" and body["ai_label"] is None


async def test_grammar_flow_cache_quota_permissions_and_validation(
    app: FastAPI, client: httpx.AsyncClient, grammar_llm: dict[str, Any]
) -> None:
    owner, other = await register(client), await register(client)
    admin: Account = await make_admin(app, client)
    await _drain(_worker(app))
    _, bubbles = await _ready_page(client, app, owner)
    bubble_id = bubbles[0]["id"]
    await _set_bubble_text(app, bubble_id, SENTENCE)
    url = f"{API}/bubbles/{bubble_id}/grammar"

    # Khách → 401; người khác không đọc được truyện riêng tư → 404.
    assert (await client.post(url)).status_code == 401
    assert (await client.post(url, headers=other.headers)).status_code == 404

    # Lần đầu: gọi LLM, kết quả hợp lệ kèm nhãn nguồn AI; tốn 1 lượt.
    first = await client.post(url, headers=owner.headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert (body["status"], body["cached"], body["sentence"]) == ("ok", False, SENTENCE)
    assert body["ai_label"] == "Do AI phân tích, có thể chưa chính xác"
    assert [n["label_vi"] for n in body["tree"]] == ["chủ ngữ", "trạng ngữ", "vị ngữ"]
    assert body["tree"][1]["children"][0]["label"] == "preposition"
    assert body["points"][0]["pattern"] == "把 + 宾语 + 动词"
    assert await _scalar(app, "SELECT count(*) FROM grammar_requests WHERE user_id = :u", u=owner.id) == 1

    # Lần hai (và quản trị): lấy từ bộ nhớ dùng chung, không gọi LLM, không tốn thêm lượt dù hạn mức đã hết.
    again = await client.post(url, headers=owner.headers)
    assert again.json()["cached"] is True and again.json()["tree"] == body["tree"]
    assert (await client.post(url, headers=admin.headers)).json()["cached"] is True
    assert len(grammar_llm["analyzer"].requests) == 1
    assert await _scalar(app, "SELECT count(*) FROM grammar_requests WHERE user_id = :u", u=owner.id) == 1

    # Câu mới khi đã hết hạn mức ngày → trạng thái nhẹ, không gọi LLM.
    await _set_bubble_text(app, bubble_id, "你好，朋友。")
    limited = await client.post(url, headers=owner.headers)
    assert limited.status_code == 200 and limited.json()["status"] == "limit_reached"
    assert limited.json()["message"] and len(grammar_llm["analyzer"].requests) == 1

    # Văn bản không có chữ Hán → 400.
    await _set_bubble_text(app, bubble_id, "123 ???")
    bad = await client.post(url, headers=owner.headers)
    assert (bad.status_code, error_code(bad)) == (400, "BUBBLE_HAS_NO_HAN")
    assert (await client.post(f"{API}/bubbles/999999999/grammar", headers=owner.headers)).status_code == 404


async def test_grammar_invalid_result_is_not_cached(
    app: FastAPI, client: httpx.AsyncClient, grammar_llm: dict[str, Any]
) -> None:
    grammar_llm["analyzer"] = FakeAnalyzer({"tree": [{"label": "noun", "text": "x"}], "points": []})
    grammar_llm["limit"] = 5
    owner = await register(client)
    await _drain(_worker(app))
    _, bubbles = await _ready_page(client, app, owner)
    bubble_id = bubbles[0]["id"]
    await _set_bubble_text(app, bubble_id, SENTENCE)
    res = await client.post(f"{API}/bubbles/{bubble_id}/grammar", headers=owner.headers)
    assert res.json()["status"] == "unanalyzable" and res.json()["message"] == "Chưa phân tích được câu này"
    assert (
        await _scalar(
            app, "SELECT count(*) FROM grammar_analyses WHERE sentence_hash = :h", h=sentence_hash(SENTENCE)
        )
        == 0
    )
    assert (
        await _scalar(
            app,
            "SELECT count(*) FROM grammar_requests WHERE user_id = :u AND analysis_id IS NULL",
            u=owner.id,
        )
        == 1
    )


# --------------------------------------------------------------------------- F09.10
async def _submitted_quiz(
    app: FastAPI, client: httpx.AsyncClient, who: Account
) -> tuple[int, list[dict[str, Any]]]:
    for term in TERMS:
        res = await client.post(
            f"{API}/vocab-entries", json={"term": term, "source": "manual"}, headers=who.headers
        )
        assert res.status_code == 201, res.text
    created = await client.post(QUIZZES, json={"question_count": 5}, headers=who.headers)
    quiz = created.json()
    assert "has_mistake_review" not in json.dumps(quiz)  # bài chưa nộp không có cờ
    async with app.state.container.session_factory() as session:
        rows = await session.execute(
            text("SELECT id, correct_answer FROM quiz_questions WHERE quiz_id = :q"), {"q": quiz["id"]}
        )
        correct = {r[0]: r[1] for r in rows}
    questions = quiz["questions"]
    answers = [{"question_id": questions[0]["id"], "answer": correct[questions[0]["id"]]}]
    answers.append({"question_id": questions[1]["id"], "answer": "chắc chắn sai"})
    submitted = await client.post(
        f"{QUIZZES}/{quiz['id']}/submit", json={"answers": answers}, headers=who.headers
    )
    assert submitted.status_code == 200, submitted.text
    return quiz["id"], submitted.json()["questions"]


async def test_mistake_review_flow_fallback_flags_permissions_and_no_side_effects(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner, other = await register(client), await register(client)
    quiz_id, questions = await _submitted_quiz(app, client, owner)
    right, wrong = questions[0], questions[1]
    base = f"{QUIZZES}/{quiz_id}/questions"

    # Bài đã nộp: cờ chỉ bật sau khi có "Vì sao sai?".
    assert wrong["has_mistake_review"] is False and right["has_mistake_review"] is False
    for method_url in (f"{base}/{wrong['id']}/mistake-review",):
        assert (await client.post(method_url)).status_code == 401
        assert (await client.post(method_url, headers=other.headers)).status_code == 404

    # Câu đúng → 400; câu không thuộc bài → 404.
    not_wrong = await client.post(f"{base}/{right['id']}/mistake-review", headers=owner.headers)
    assert (not_wrong.status_code, error_code(not_wrong)) == (400, "QUESTION_NOT_WRONG")
    missing = await client.post(f"{base}/999999999/mistake-review", headers=owner.headers)
    assert (missing.status_code, error_code(missing)) == (404, "QUIZ_QUESTION_NOT_FOUND")

    # Câu sai: LLM tắt → bản dự phòng với giải thích có sẵn; không lộ đáp án câu luyện.
    scores_before = (await client.get(f"{QUIZZES}/{quiz_id}", headers=owner.headers)).json()["score"]
    logs_before = await _scalar(app, "SELECT count(*) FROM review_logs WHERE user_id = :u", u=owner.id)
    res = await client.post(f"{base}/{wrong['id']}/mistake-review", headers=owner.headers)
    assert res.status_code == 200, res.text
    review = res.json()
    assert (review["origin"], review["cached"], review["ai_label"]) == ("fallback", False, None)
    assert review["explanation"] == wrong["explanation"]
    assert review["practice"] is None or set(review["practice"]) == {"prompt", "options"}
    again = await client.post(f"{base}/{wrong['id']}/mistake-review", headers=owner.headers)
    assert again.json()["cached"] is True and again.json()["explanation"] == review["explanation"]

    # Cờ bật ở kết quả bài (kể cả mở lại từ lịch sử).
    reopened = (await client.get(f"{QUIZZES}/{quiz_id}", headers=owner.headers)).json()
    flags = {q["id"]: q["has_mistake_review"] for q in reopened["questions"]}
    assert flags[wrong["id"]] is True and flags[right["id"]] is False

    # Câu luyện (dựng trực tiếp vào CSDL để không phụ thuộc kho ví dụ): chấm ở máy chủ, không lưu gì.
    stored = {
        "origin": "llm",
        "explanation": review["explanation"],
        "difference": "khác nhau",
        "practice": {
            "prompt": "“一” nghĩa là gì?",
            "options": ["một", "hai", "ba", "bốn"],
            "answer": "một",
            "explanation": "一 là một",
        },
    }
    async with app.state.container.session_factory() as session:
        await session.execute(
            text("UPDATE quiz_questions SET mistake_review = CAST(:j AS jsonb) WHERE id = :i"),
            {"j": json.dumps(stored, ensure_ascii=False), "i": wrong["id"]},
        )
        await session.commit()
    shown = (await client.post(f"{base}/{wrong['id']}/mistake-review", headers=owner.headers)).json()
    assert shown["practice"] == {"prompt": "“一” nghĩa là gì?", "options": ["một", "hai", "ba", "bốn"]}
    assert shown["ai_label"] == "Do AI viết, có thể chưa chính xác"
    answer_url = f"{base}/{wrong['id']}/mistake-review/answer"
    bad = await client.post(answer_url, json={"choice": "hai"}, headers=owner.headers)
    assert bad.status_code == 200 and bad.json() == {
        "is_correct": False,
        "correct_answer": "một",
        "explanation": "一 là một",
    }
    assert (await client.post(answer_url, json={"choice": "một"}, headers=owner.headers)).json()["is_correct"]
    invalid = await client.post(answer_url, json={"choice": "năm"}, headers=owner.headers)
    assert (invalid.status_code, error_code(invalid)) == (400, "INVALID_PRACTICE_CHOICE")
    assert (await client.post(answer_url, json={"choice": "một"}, headers=other.headers)).status_code == 404
    assert (await client.post(answer_url, json={"choice": ""}, headers=owner.headers)).status_code == 422

    # Không đổi điểm bài, không ghi lượt ôn.
    assert (await client.get(f"{QUIZZES}/{quiz_id}", headers=owner.headers)).json()["score"] == scores_before
    assert (
        await _scalar(app, "SELECT count(*) FROM review_logs WHERE user_id = :u", u=owner.id) == logs_before
    )


async def test_mistake_review_rejected_for_unsubmitted_quiz(app: FastAPI, client: httpx.AsyncClient) -> None:
    owner = await register(client)
    for term in TERMS:
        await client.post(
            f"{API}/vocab-entries", json={"term": term, "source": "manual"}, headers=owner.headers
        )
    quiz = (await client.post(QUIZZES, json={"question_count": 5}, headers=owner.headers)).json()
    url = f"{QUIZZES}/{quiz['id']}/questions/{quiz['questions'][0]['id']}/mistake-review"
    res = await client.post(url, headers=owner.headers)
    assert (res.status_code, error_code(res)) == (409, "QUIZ_NOT_SUBMITTED")
