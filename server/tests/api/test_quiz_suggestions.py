"""M09 Kiểm tra + M10 Gợi ý từ — luồng chính, phân quyền, ôn sớm (F09.01–F09.08, F10.01–F10.03, F13.07).

Đề dự phòng được dùng vì LLM tắt (mặc định); câu trả lời đúng lấy từ CSDL kiểm thử để chấm điểm thật.
"""

from __future__ import annotations

import random
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.api.test_imaging_reader import _drain, _new_page, _worker
from tests.api.test_vocab_review import _ready_page
from tests.helpers import Account, error_code, make_admin, register

pytestmark = pytest.mark.integration

API = "/api/v1"
QUIZZES = f"{API}/quizzes"
TERMS = list("一二三四五六七八九十百千")  # 12 từ chữ Hán đơn lẻ


async def _save_words(client: httpx.AsyncClient, who: Account, terms: list[str]) -> list[int]:
    ids = []
    for term in terms:
        res = await client.post(
            f"{API}/vocab-entries", json={"term": term, "source": "manual"}, headers=who.headers
        )
        assert res.status_code == 201, res.text
        ids.append(res.json()["entry"]["id"])
    return ids


async def _correct_answers(app: FastAPI, quiz_id: int) -> dict[int, str]:
    async with app.state.container.session_factory() as session:
        rows = await session.execute(
            text("SELECT id, correct_answer FROM quiz_questions WHERE quiz_id = :q"), {"q": quiz_id}
        )
        return {r[0]: r[1] for r in rows}


async def _audit_actions(app: FastAPI, admin_id: int) -> list[str]:
    async with app.state.container.session_factory() as session:
        rows = await session.execute(
            text("SELECT action FROM admin_audit_logs WHERE admin_id = :a ORDER BY id"), {"a": admin_id}
        )
        return [r[0] for r in rows]


async def test_quiz_create_hidden_answers_submit_reschedule_and_permissions(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-45..50: đủ từ mới tạo được, không lộ đáp án, nộp một lần, từ sai về ôn sớm, quyền truy cập."""
    owner, other = await register(client), await register(client)
    admin = await make_admin(app, client)

    for method, url in (
        ("GET", f"{QUIZZES}/summary"),
        ("POST", QUIZZES),
        ("GET", QUIZZES),
        ("GET", f"{QUIZZES}/1"),
    ):
        assert (await client.request(method, url)).status_code == 401, (method, url)

    # F09.01: dưới 10 từ → 400 kèm số từ hiện có; số câu ngoài 5..20 → 422.
    summary = (await client.get(f"{QUIZZES}/summary", headers=owner.headers)).json()
    assert summary == {"eligible_words": 0, "min_words": 10, "question_count": 10, "llm_enabled": False}
    few = await client.post(QUIZZES, json={}, headers=owner.headers)
    assert (few.status_code, error_code(few)) == (400, "NOT_ENOUGH_WORDS_FOR_QUIZ")
    assert few.json()["error"]["details"] == {"current": 0, "required": 10}
    assert (await client.post(QUIZZES, json={"question_count": 3}, headers=owner.headers)).status_code == 422
    assert (await client.get(QUIZZES, headers=owner.headers)).json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
    }

    # 12 từ, 1 từ "Bỏ qua" không tính; toàn bộ từ còn lại "Đã thuộc" nên chưa có thẻ nào đến hạn.
    ids = await _save_words(client, owner, TERMS)
    for i, entry_id in enumerate(ids):
        status = "ignored" if i == 0 else "known"
        res = await client.patch(
            f"{API}/vocab-entries/{entry_id}", json={"status": status}, headers=owner.headers
        )
        assert res.status_code == 200, res.text
    assert (await client.get(f"{QUIZZES}/summary", headers=owner.headers)).json()["eligible_words"] == 11
    assert (await client.get(f"{API}/cards/due", headers=owner.headers)).json()["total"] == 0

    # F09.01/F09.08: tạo bài 5 câu bằng đề dự phòng; câu hỏi không lộ đáp án.
    created = await client.post(QUIZZES, json={"question_count": 5}, headers=owner.headers)
    assert created.status_code == 201, created.text
    quiz = created.json()
    assert (quiz["status"], quiz["source"], quiz["question_count"], quiz["score"]) == (
        "in_progress",
        "fallback",
        5,
        None,
    )
    assert quiz["note"] == "Đề tạo tự động từ từ điển"
    questions = quiz["questions"]
    assert [q["position"] for q in questions] == [1, 2, 3, 4, 5]
    hidden = {"correct_answer", "accepted_answers", "explanation", "is_correct", "user_answer"}
    assert all(not hidden & set(q) for q in questions)
    assert all(q["options"] is None or len(q["options"]) == 4 for q in questions)
    quiz_id = quiz["id"]
    reopened = (await client.get(f"{QUIZZES}/{quiz_id}", headers=owner.headers)).json()
    assert all(not hidden & set(q) for q in reopened["questions"])

    # US-NH-46 TC5, US-NH-49 TC4: bài của người khác → 404 (xem, nộp); khách → 401.
    for who in (other,):
        assert (await client.get(f"{QUIZZES}/{quiz_id}", headers=who.headers)).status_code == 404
        res = await client.post(f"{QUIZZES}/{quiz_id}/submit", json={"answers": []}, headers=who.headers)
        assert (res.status_code, error_code(res)) == (404, "QUIZ_NOT_FOUND")
    assert (await client.get(QUIZZES, headers=other.headers)).json()["total"] == 0

    # F09.02: câu hỏi không thuộc bài → 400, bài vẫn chưa nộp.
    bad = await client.post(
        f"{QUIZZES}/{quiz_id}/submit",
        json={"answers": [{"question_id": 999999999, "answer": "x"}]},
        headers=owner.headers,
    )
    assert (bad.status_code, error_code(bad)) == (400, "INVALID_QUIZ_ANSWERS")

    # F09.03/F09.04: đúng 3 câu, sai 1 câu, bỏ trống 1 câu.
    correct = await _correct_answers(app, quiz_id)
    answers = [{"question_id": questions[i]["id"], "answer": correct[questions[i]["id"]]} for i in range(3)]
    answers.append({"question_id": questions[3]["id"], "answer": "chắc chắn sai"})
    submitted = await client.post(
        f"{QUIZZES}/{quiz_id}/submit", json={"answers": answers}, headers=owner.headers
    )
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert (result["status"], result["score"], result["question_count"]) == ("submitted", 3, 5)
    assert [q["is_correct"] for q in result["questions"]] == [True, True, True, False, False]
    assert all(q["correct_answer"] and q["explanation"] for q in result["questions"])
    assert result["questions"][4]["user_answer"] is None
    assert len(result["rescheduled_terms"]) == 2 and set(result["rescheduled_terms"]) <= set(TERMS)

    # US-NH-48: chỉ từ sai về "Đang học" và có thẻ đến hạn ngay (3 thẻ mỗi từ); từ đúng vẫn "Đã thuộc".
    due = (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()
    assert due["total"] == 6 and {c["term"] for c in due["items"]} == set(result["rescheduled_terms"])
    learning = (await client.get(f"{API}/vocab-entries?status=learning", headers=owner.headers)).json()
    assert {i["term"] for i in learning["items"]} == set(result["rescheduled_terms"])

    # US-NH-46 TC3: nộp lần hai → 409; tải lại kết quả không tính lại lịch ôn.
    again = await client.post(f"{QUIZZES}/{quiz_id}/submit", json={"answers": []}, headers=owner.headers)
    assert (again.status_code, error_code(again)) == (409, "QUIZ_ALREADY_SUBMITTED")
    reloaded = (await client.get(f"{QUIZZES}/{quiz_id}", headers=owner.headers)).json()
    assert reloaded["score"] == 3 and reloaded["questions"][0]["correct_answer"]
    assert (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["total"] == 6

    # F09.05: lịch sử mới nhất trước, gồm bài đang làm dở.
    second = (await client.post(QUIZZES, json={"question_count": 5}, headers=owner.headers)).json()
    history = (await client.get(f"{QUIZZES}?page=1&size=10", headers=owner.headers)).json()
    assert history["total"] == 2 and [i["id"] for i in history["items"]] == [second["id"], quiz_id]
    assert history["items"][1]["score"] == 3 and history["items"][0]["status"] == "in_progress"

    # F13.07: quản trị xem được, người dùng thường không; xóa ghi nhật ký.
    base = f"{API}/admin/users/{owner.id}/quizzes"
    assert (await client.get(base, headers=other.headers)).status_code == 403
    listed = (await client.get(base, headers=admin.headers)).json()
    assert listed["total"] == 2
    detail = (await client.get(f"{base}/{quiz_id}", headers=admin.headers)).json()
    assert detail["score"] == 3 and detail["questions"][0]["correct_answer"]
    assert (await client.delete(f"{base}/{quiz_id}", headers=admin.headers)).status_code == 204
    missing = await client.delete(f"{base}/{quiz_id}", headers=admin.headers)
    assert (missing.status_code, error_code(missing)) == (404, "QUIZ_NOT_FOUND")
    assert (await client.get(QUIZZES, headers=owner.headers)).json()["total"] == 1
    assert "quiz.delete" in await _audit_actions(app, admin.id)


async def _retoken(app: FastAPI, page_id: int) -> None:
    """Đổi token của bong bóng đầu thành từ không thuộc danh sách từ quá cơ bản (F10.01 loại 你好, 吗)."""
    tokens = '[{"word": "学习", "pinyin": "xué xí"}, {"word": "朋友", "pinyin": "péng yǒu"}]'
    async with app.state.container.session_factory() as session:
        await session.execute(
            text(
                "UPDATE bubbles SET text_zh = '学习朋友', tokens = CAST(:t AS jsonb) "
                "WHERE idx = 0 AND translation_id = "
                "(SELECT translation_id FROM pages WHERE id = :p)"
            ),
            {"t": tokens, "p": page_id},
        )
        await session.commit()


async def test_suggestions_list_processing_dismiss_restore_and_accept(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-51, US-NH-52: gợi ý trong chương, loại từ đã lưu/đã bỏ qua, nhận vào sổ tay, phân quyền."""
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, _ = await _ready_page(client, app, owner)
    await _retoken(app, page["id"])
    chapter_id = page["chapter_id"]
    url = f"{API}/chapters/{chapter_id}/suggestions"

    # Khách 401; người khác không đọc được chương riêng tư → 404.
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers=other.headers)).status_code == 404
    assert (
        await client.post(f"{url}/accept", json={"term": "学习"}, headers=other.headers)
    ).status_code == 404

    # F10.01: chương xong; chưa khai báo HSK → hsk_level null, thứ tự theo tần suất. Token từ bong bóng.
    first = (await client.get(url, headers=owner.headers)).json()
    assert (first["status"], first["hsk_level"]) == ("ready", None)
    terms = {i["term"]: i for i in first["items"]}
    assert set(terms) == {"学习", "朋友"}
    hello = terms["学习"]
    assert (hello["occurrences"], hello["lookups"], hello["pinyin"], hello["page_no"]) == (1, 0, "xué xí", 1)
    assert hello["page_id"] == page["id"] and hello["bubble_id"]
    limited = (await client.get(f"{url}?limit=1", headers=owner.headers)).json()
    assert len(limited["items"]) == 1

    # Trang mới chưa dịch xong → processing nhưng vẫn trả gợi ý của trang đã xong.
    await _new_page(client, owner, page["series_id"], page["chapter_id"])
    pending = (await client.get(url, headers=owner.headers)).json()
    assert pending["status"] == "processing" and {i["term"] for i in pending["items"]} == {"学习", "朋友"}

    # F10.03: bỏ qua (idempotent) → biến mất ở mọi chương; mục Đã bỏ qua; khôi phục (kể cả khi không có).
    dismissed = f"{API}/suggestions/dismissed"
    for _ in range(2):
        assert (await client.put(f"{dismissed}/朋友", headers=owner.headers)).status_code == 204
    assert (await client.put(f"{dismissed}/abc", headers=owner.headers)).status_code == 400
    after = (await client.get(url, headers=owner.headers)).json()
    assert [i["term"] for i in after["items"]] == ["学习"]
    listing = (await client.get(dismissed, headers=owner.headers)).json()
    assert (
        listing["total"] == 1
        and listing["items"][0]["term"] == "朋友"
        and listing["items"][0]["dismissed_at"]
    )
    assert (await client.get(dismissed, headers=other.headers)).json()["total"] == 0
    assert (await client.delete(f"{dismissed}/朋友", headers=owner.headers)).status_code == 204
    assert (await client.delete(f"{dismissed}/朋友", headers=owner.headers)).status_code == 204
    assert {i["term"] for i in (await client.get(url, headers=owner.headers)).json()["items"]} == {
        "学习",
        "朋友",
    }

    # F10.02: nhận gợi ý → như lưu từ thường (nguồn suggestion, kèm ngữ cảnh, 3 thẻ), rồi biến mất khỏi gợi ý.
    accepted = await client.post(f"{url}/accept", json={"term": "学习"}, headers=owner.headers)
    assert accepted.status_code == 201, accepted.text
    body = accepted.json()
    assert (body["created"], body["context_added"], body["cards_created"]) == (True, True, 3)
    assert body["entry"]["source"] == "suggestion" and body["entry"]["term"] == "学习"
    assert body["entry"]["contexts"][0]["sentence_zh"] == "学习朋友"
    assert [i["term"] for i in (await client.get(url, headers=owner.headers)).json()["items"]] == ["朋友"]

    # US-NH-32: nhận lại từ đã có với đúng ngữ cảnh đó → 409; từ không có trong chương → 404.
    dup = await client.post(f"{url}/accept", json={"term": "学习"}, headers=owner.headers)
    assert (dup.status_code, error_code(dup)) == (409, "VOCAB_CONTEXT_ALREADY_SAVED")
    absent = await client.post(f"{url}/accept", json={"term": "再见"}, headers=owner.headers)
    assert (absent.status_code, error_code(absent)) == (404, "SUGGESTION_NOT_FOUND")
    invalid = await client.post(f"{url}/accept", json={"term": "abc"}, headers=owner.headers)
    assert (invalid.status_code, error_code(invalid)) == (400, "INVALID_TERM")


async def test_suggestions_use_declared_hsk_level(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-51 TC1/TC3: đã khai báo trình độ thì `hsk_level` được trả về để giao diện bỏ lời nhắc."""
    owner = await register(client)
    await _drain(_worker(app))
    page, _ = await _ready_page(client, app, owner)
    await _retoken(app, page["id"])
    patched = await client.patch(f"{API}/settings", json={"hsk_level": 3}, headers=owner.headers)
    assert patched.status_code == 200, patched.text
    res: dict[str, Any] = (
        await client.get(f"{API}/chapters/{page['chapter_id']}/suggestions", headers=owner.headers)
    ).json()
    assert res["hsk_level"] == 3 and len(res["items"]) == 2
    assert all(0 <= i["score"] <= 1 for i in res["items"])


async def _seed_related_words(app: FastAPI, saved: list[str]) -> list[str]:
    """Từ HSK cấp 2 chứa chữ đã lưu, có nghĩa và câu ví dụ Tatoeba đã tính độ khó (dữ liệu dựng cho test)."""
    related = [f"{ch}{chr(ord(ch) + 0x300)}" for ch in saved[:4]]
    async with app.state.container.session_factory() as session:
        for word in saved:  # từ đã lưu phải có trong từ điển mới được làm cầu nối (F09.09)
            await session.execute(
                text(
                    "INSERT INTO dict_entries (simplified, pinyin, pinyin_numeric, pinyin_search, "
                    "meanings_vi, source) VALUES (:w, 'ni', 'ni3', 'ni', CAST(:mv AS jsonb), 'cvdict') "
                    "ON CONFLICT (simplified, pinyin_numeric, source) DO NOTHING"
                ),
                {"w": word, "mv": '[{"src": "cvdict", "gloss": "nghĩa từ đã lưu"}]'},
            )
        for index, word in enumerate(related):
            await session.execute(
                text(
                    "INSERT INTO hsk_words (word, level, list_version) VALUES (:w, 2, '3.0') "
                    "ON CONFLICT (word) DO UPDATE SET level = 2"
                ),
                {"w": word},
            )
            entry_id = (
                await session.execute(
                    text(
                        "INSERT INTO dict_entries (simplified, pinyin, pinyin_numeric, pinyin_search, "
                        "meanings_vi, source) VALUES (:w, 'ni', 'ni3', 'ni', CAST(:mv AS jsonb), 'cvdict') "
                        "ON CONFLICT (simplified, pinyin_numeric, source) DO UPDATE SET pinyin = 'ni' "
                        "RETURNING id"
                    ),
                    {"w": word, "mv": '[{"src": "cvdict", "gloss": "nghĩa thử nghiệm"}]'},
                )
            ).scalar_one()
            await session.execute(text("DELETE FROM dict_examples WHERE entry_id = :e"), {"e": entry_id})
            await session.execute(
                text(
                    "INSERT INTO dict_examples (entry_id, zh, vi, source, difficulty_level) "
                    "VALUES (:e, :zh, :vi, 'tatoeba', 2)"
                ),
                {"e": entry_id, "zh": f"这是{word}的好句子", "vi": f"Câu thử số {index}"},
            )
        await session.commit()
    return related


async def _drop_related_words(app: FastAPI, related: list[str]) -> None:
    """Dọn dữ liệu dựng riêng cho test để không ảnh hưởng các test từ điển khác (vd. từ của ngày)."""
    async with app.state.container.session_factory() as session:
        await session.execute(
            text(
                "DELETE FROM dict_examples WHERE entry_id IN "
                "(SELECT id FROM dict_entries WHERE simplified = ANY(:w) AND source = 'cvdict')"
            ),
            {"w": related},
        )
        await session.execute(
            text("DELETE FROM dict_entries WHERE simplified = ANY(:w) AND source = 'cvdict'"), {"w": related}
        )
        await session.execute(text("DELETE FROM hsk_words WHERE word = ANY(:w)"), {"w": related})
        await session.commit()


async def test_quiz_related_words_examples_separate_scores_and_save_word(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """F09.09, US-NH-69: từ mở rộng + câu ví dụ, điểm riêng, ôn sớm bỏ qua câu mở rộng, lưu từ sau khi nộp."""
    owner, other = await register(client), await register(client)
    base = random.randrange(0x3400, 0x3400 + 3000)
    saved_terms = [chr(base + i) for i in range(12)]
    related_terms = await _seed_related_words(app, saved_terms)
    try:
        await _save_words(client, owner, saved_terms)
        await _related_flow(app, client, owner, other, saved_terms, related_terms)
    finally:
        await _drop_related_words(app, [*saved_terms, *related_terms])


async def _related_flow(
    app: FastAPI,
    client: httpx.AsyncClient,
    owner: Account,
    other: Account,
    saved_terms: list[str],
    related_terms: list[str],
) -> None:
    created = await client.post(QUIZZES, json={"question_count": 10}, headers=owner.headers)
    assert created.status_code == 201, created.text
    quiz = created.json()
    quiz_id = quiz["id"]
    assert (quiz["question_count"], quiz["related_count"], quiz["related_score"]) == (8, 2, None)
    questions = quiz["questions"]
    assert len(questions) == 10
    extra = [q for q in questions if q["target_kind"] == "related"]
    assert len(extra) == 2 and all(q["target_kind"] == "saved" for q in questions if q not in extra)
    for q in extra:
        assert q["question_type"] == "multiple_choice" and q["hint"] and q["hint"] not in q["prompt"]
        assert q["hint"].startswith("Gợi ý: chữ ")
    # Chưa nộp: không lộ từ, đáp án, vi của câu ví dụ.
    hidden = {"term", "correct_answer", "related_to", "can_save", "is_correct", "explanation"}
    assert all(not hidden & set(q) for q in questions)
    assert all("vi" not in (q["example"] or {}) for q in questions)
    for q in extra:  # từ mở rộng không được lộ trong câu hỏi dạng điền từ
        if q["example"] is None:
            assert not any(term in q["prompt"] for term in related_terms)

    # Chưa nộp thì chưa lưu được từ (409).
    first_extra = extra[0]
    early = await client.post(
        f"{QUIZZES}/{quiz_id}/questions/{first_extra['id']}/save-word", headers=owner.headers
    )
    assert (early.status_code, error_code(early)) == (409, "QUIZ_NOT_SUBMITTED")

    # Nộp: đúng hết câu từ mở rộng, sai hết câu từ đã lưu → điểm tính riêng.
    correct = await _correct_answers(app, quiz_id)
    answers = [
        {"question_id": q["id"], "answer": correct[q["id"]] if q["target_kind"] == "related" else "sai"}
        for q in questions
    ]
    done = await client.post(f"{QUIZZES}/{quiz_id}/submit", json={"answers": answers}, headers=owner.headers)
    assert done.status_code == 200, done.text
    result = done.json()
    assert (result["score"], result["question_count"]) == (0, 8)
    assert (result["related_score"], result["related_count"]) == (2, 2)
    assert set(result["rescheduled_terms"]) <= set(saved_terms) and len(result["rescheduled_terms"]) == 8
    shown = {q["id"]: q for q in result["questions"]}
    for q in extra:
        item = shown[q["id"]]
        assert item["term"] in related_terms and item["can_save"] is True and item["is_correct"] is True
        assert item["related_to"]["term"] in saved_terms and item["vocab_entry_id"] is None
    saved_item = next(q for q in result["questions"] if q["target_kind"] == "saved")
    assert saved_item["can_save"] is False and saved_item["related_to"] is None
    due = (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()
    assert {c["term"] for c in due["items"]} <= set(saved_terms)  # câu từ mở rộng không tạo thẻ ôn

    # Lưu từ mở rộng sau khi xem kết quả; câu từ đã lưu và bài của người khác bị từ chối.
    url = f"{QUIZZES}/{quiz_id}/questions/{first_extra['id']}/save-word"
    saved = await client.post(url, headers=owner.headers)
    assert saved.status_code == 201, saved.text
    entry = saved.json()["entry"]
    assert (entry["term"], entry["source"]) == (shown[first_extra["id"]]["term"], "quiz")
    assert (await client.post(url, headers=owner.headers)).status_code == 200
    not_savable = await client.post(
        f"{QUIZZES}/{quiz_id}/questions/{saved_item['id']}/save-word", headers=owner.headers
    )
    assert (not_savable.status_code, error_code(not_savable)) == (400, "WORD_NOT_SAVABLE")
    assert (await client.post(url, headers=other.headers)).status_code == 404
    missing = await client.post(f"{QUIZZES}/{quiz_id}/questions/999999999/save-word", headers=owner.headers)
    assert (missing.status_code, error_code(missing)) == (404, "QUIZ_QUESTION_NOT_FOUND")
    reopened = (await client.get(f"{QUIZZES}/{quiz_id}", headers=owner.headers)).json()
    flags = {q["id"]: q["can_save"] for q in reopened["questions"] if q["target_kind"] == "related"}
    assert flags[first_extra["id"]] is False and flags[extra[1]["id"]] is True
