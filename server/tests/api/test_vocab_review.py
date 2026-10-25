"""M07 Sổ tay + M08 Ôn tập — luồng chính, phân quyền, chống trùng (F07.01–F07.07, F08.01–F08.07, F08.09).

Bong bóng dựng bằng cách cho worker giả hoàn tất bản dịch trong CSDL kiểm thử (không chạy YOLO/OCR);
giờ hệ thống thay bằng đồng hồ giả để kiểm tra lịch ôn.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.api.test_imaging_reader import _complete, _drain, _new_page, _translation_id, _worker
from tests.conftest import FixedClock
from tests.helpers import Account, error_code, register

pytestmark = pytest.mark.integration

API = "/api/v1"
VOCAB = f"{API}/vocab-entries"


async def _ready_page(
    client: httpx.AsyncClient,
    app: FastAPI,
    who: Account,
    series_id: int | None = None,
    chapter_id: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Trang đã dịch xong với hai bong bóng: "你好吗" (có token) và "咚"."""
    jobs = _worker(app)
    page = await _new_page(client, who, series_id, chapter_id)
    await _complete(jobs, await _translation_id(client, who, page["id"]))
    reading = (await client.get(f"{API}/pages/{page['id']}/reading", headers=who.headers)).json()
    return page, reading["bubbles"]


def _save_body(term: str, bubble: dict[str, Any] | None = None, page_id: int | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"term": term, "source": "highlight" if bubble else "manual"}
    if bubble:
        body["bubble_id"] = bubble["id"]
    if page_id:
        body["page_id"] = page_id
    return body


async def test_vocab_save_dedupe_filter_update_and_delete(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-31..37: lưu kèm ngữ cảnh + 3 thẻ, chống trùng, thêm ngữ cảnh, lọc, sửa, xóa; phân quyền."""
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    pid, first_bubble = page["id"], bubbles[0]

    # Khách → 401 ở mọi endpoint của sổ tay và thẻ.
    for method, url in (
        ("POST", VOCAB),
        ("GET", VOCAB),
        ("GET", f"{VOCAB}/decks"),
        ("GET", f"{VOCAB}/1"),
        ("PATCH", f"{VOCAB}/1"),
        ("DELETE", f"{VOCAB}/1"),
        ("DELETE", f"{VOCAB}/1/contexts/1"),
        ("GET", f"{API}/cards/due"),
        ("POST", f"{API}/cards/1/grade"),
        ("GET", f"{API}/review/summary"),
    ):
        assert (await client.request(method, url)).status_code == 401, (method, url)

    # F07.01: lưu từ mới → 201, đủ ngữ cảnh + ảnh cắt + 3 thẻ.
    saved = await client.post(VOCAB, json=_save_body("你好", first_bubble, pid), headers=owner.headers)
    assert saved.status_code == 201, saved.text
    body = saved.json()
    assert (body["created"], body["context_added"], body["cards_created"], body["snippet_missing"]) == (
        True,
        True,
        3,
        False,
    )
    entry = body["entry"]
    assert (entry["term"], entry["status"], entry["source"], entry["pinyin"]) == (
        "你好",
        "learning",
        "highlight",
        "nǐ hǎo",
    )
    assert entry["hsk_source"] in {"list", "derived", "none"} and entry["is_due"] is True
    assert entry["srs"]["card_count"] == 3 and len(entry["cards"]) == 3
    assert {c["card_type"] for c in entry["cards"]} == {"recognition", "recall", "listening"}
    context = entry["contexts"][0]
    assert (context["sentence_zh"], context["sentence_vi"]) == ("你好吗", "Bạn khỏe không")
    assert context["source"]["series_id"] == page["series_id"] and context["source"]["page_no"] == 1
    assert context["source_label"] == f"Hoa Hồng · Chương 1 · Trang {context['source']['page_no']}"
    entry_id = entry["id"]

    # Ảnh ngữ cảnh: chủ sở hữu xem được, người khác/khách không (kind snippet là riêng tư).
    snippet = await client.get(context["snippet_url"], headers=owner.headers)
    assert snippet.status_code == 200 and snippet.headers["content-type"] == "image/png"
    assert (await client.get(context["snippet_url"], headers=other.headers)).status_code == 404
    assert (await client.get(context["snippet_url"])).status_code == 404

    # F07.02: lưu lại đúng bong bóng → 409; người khác không lưu được từ bong bóng riêng tư → 404.
    dup = await client.post(VOCAB, json=_save_body("你好", first_bubble, pid), headers=owner.headers)
    assert (dup.status_code, error_code(dup)) == (409, "VOCAB_CONTEXT_ALREADY_SAVED")
    assert dup.json()["error"]["details"]["vocab_entry_id"] == entry_id
    foreign = await client.post(VOCAB, json=_save_body("你好", first_bubble), headers=other.headers)
    assert (foreign.status_code, error_code(foreign)) == (404, "BUBBLE_NOT_FOUND")
    wrong = await client.post(VOCAB, json=_save_body("再见", first_bubble, pid), headers=owner.headers)
    assert (wrong.status_code, error_code(wrong)) == (400, "TERM_NOT_IN_BUBBLE")
    bad_term = await client.post(VOCAB, json={"term": "abc", "source": "manual"}, headers=owner.headers)
    assert (bad_term.status_code, error_code(bad_term)) == (400, "INVALID_TERM")
    bad_source = await client.post(VOCAB, json={"term": "你好", "source": "x"}, headers=owner.headers)
    assert (bad_source.status_code, error_code(bad_source)) == (400, "INVALID_VOCAB_SOURCE")

    # F07.02: cùng từ ở trang khác → 200, chỉ thêm ngữ cảnh, không tạo thẻ, lịch ôn giữ nguyên.
    before = (await client.get(f"{VOCAB}/{entry_id}", headers=owner.headers)).json()["cards"]
    page2, bubbles2 = await _ready_page(client, app, owner, page["series_id"], page["chapter_id"])
    again = await client.post(VOCAB, json=_save_body("你好", bubbles2[0], page2["id"]), headers=owner.headers)
    assert again.status_code == 200, again.text
    assert (again.json()["created"], again.json()["context_added"], again.json()["cards_created"]) == (
        False,
        True,
        0,
    )
    detail = (await client.get(f"{VOCAB}/{entry_id}", headers=owner.headers)).json()
    assert len(detail["contexts"]) == 2 and detail["contexts_count"] == 2
    assert [(c["id"], c["due_at"]) for c in detail["cards"]] == [(c["id"], c["due_at"]) for c in before]

    # F07.02: hai lần bấm nhanh chỉ một mục và một bộ thẻ (một yêu cầu thắng, một thua).
    race = await asyncio.gather(
        *[
            client.post(VOCAB, json=_save_body("吗", first_bubble, pid), headers=owner.headers)
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in race) == [201, 409]
    assert error_code(next(r for r in race if r.status_code == 409)) == "VOCAB_CONTEXT_ALREADY_SAVED"

    # F07.01: từ nhập tay (không bong bóng) vẫn có đủ 3 thẻ nhưng không có ngữ cảnh.
    manual = await client.post(
        VOCAB, json={"term": "学生", "source": "manual", "meaning_vi": "học sinh"}, headers=owner.headers
    )
    assert manual.status_code == 201 and manual.json()["entry"]["contexts"] == []
    assert manual.json()["cards_created"] == 3 and manual.json()["entry"]["meaning_vi"] == "học sinh"
    manual_id = manual.json()["entry"]["id"]

    # F07.07: danh sách, bộ lọc và phân trang; chỉ dữ liệu của chính người dùng.
    listing = (await client.get(VOCAB, headers=owner.headers)).json()
    assert listing["total"] == 3 and [i["term"] for i in listing["items"]] == ["学生", "吗", "你好"]
    item = next(i for i in listing["items"] if i["term"] == "你好")
    assert item["contexts_count"] == 2 and item["first_context"]["snippet_url"].startswith(f"{API}/files/")
    assert item["is_due"] is True and item["srs"]["due_count"] == 3
    assert (await client.get(VOCAB, headers=other.headers)).json()["total"] == 0
    assert (await client.get(f"{VOCAB}?page=1&size=2", headers=owner.headers)).json()["items"][1][
        "term"
    ] == "吗"
    assert (await client.get(f"{VOCAB}?size=101", headers=owner.headers)).status_code == 422
    assert (await client.get(VOCAB, params={"q": "学"}, headers=owner.headers)).json()["total"] == 1
    assert (await client.get(VOCAB, params={"q": "học sinh"}, headers=owner.headers)).json()["total"] == 1
    assert (await client.get(VOCAB, params={"q": "%"}, headers=owner.headers)).json()["total"] == 0
    in_series = (await client.get(f"{VOCAB}?series_id={page['series_id']}", headers=owner.headers)).json()
    assert {i["term"] for i in in_series["items"]} == {"你好", "吗"}
    assert (await client.get(f"{VOCAB}?series_id=999999", headers=owner.headers)).json()["total"] == 0
    levels = [i["hsk_level"] for i in listing["items"]]
    assert (await client.get(f"{VOCAB}?hsk=none", headers=owner.headers)).json()["total"] == levels.count(
        None
    )
    for level in range(1, 10):
        got = (await client.get(f"{VOCAB}?hsk={level}", headers=owner.headers)).json()["total"]
        assert got == levels.count(level), level
    for param in ("status=known", "starred=true"):
        assert (await client.get(f"{VOCAB}?{param}", headers=owner.headers)).json()["total"] == 0
    bad_hsk = await client.get(f"{VOCAB}?hsk=12", headers=owner.headers)
    assert (bad_hsk.status_code, error_code(bad_hsk)) == (400, "INVALID_HSK_FILTER")
    bad_status = await client.get(f"{VOCAB}?status=mastered", headers=owner.headers)
    assert (bad_status.status_code, error_code(bad_status)) == (400, "INVALID_VOCAB_STATUS")

    # F07.03, F07.04: trạng thái, ghi chú (văn bản thuần), sao; giá trị sai bị từ chối; người khác 404.
    url = f"{VOCAB}/{entry_id}"
    patched = await client.patch(
        url, json={"status": "known", "note": " <b>mẹo</b> ", "is_starred": True}, headers=owner.headers
    )
    assert patched.status_code == 200, patched.text
    assert (patched.json()["status"], patched.json()["note"], patched.json()["is_starred"]) == (
        "known",
        "<b>mẹo</b>",
        True,
    )
    assert patched.json()["is_due"] is False  # từ đã thuộc không tham gia lịch ôn
    bad_note = await client.patch(url, json={"note": "a" * 1001}, headers=owner.headers)
    assert (bad_note.status_code, error_code(bad_note)) == (400, "NOTE_TOO_LONG")
    bad_value = await client.patch(url, json={"status": "mastered"}, headers=owner.headers)
    assert (bad_value.status_code, error_code(bad_value)) == (400, "INVALID_VOCAB_STATUS")
    assert (await client.patch(url, json={"note": ""}, headers=owner.headers)).json()["note"] is None
    assert (await client.patch(url, json={"note": "x"}, headers=other.headers)).status_code == 404
    assert (await client.get(url, headers=other.headers)).status_code == 404
    assert (await client.delete(url, headers=other.headers)).status_code == 404
    assert (await client.get(f"{VOCAB}?starred=true&status=known", headers=owner.headers)).json()[
        "total"
    ] == 1

    # F07.05: xóa từng ngữ cảnh (kể cả cuối cùng) — từ và thẻ giữ nguyên, ảnh cắt biến mất.
    contexts = (await client.get(url, headers=owner.headers)).json()["contexts"]
    ctx_url = f"{url}/contexts/{contexts[0]['id']}"
    assert (await client.delete(ctx_url, headers=other.headers)).status_code == 404
    for ctx in contexts:
        res = await client.delete(f"{url}/contexts/{ctx['id']}", headers=owner.headers)
        assert res.status_code == 204
        assert (await client.get(ctx["snippet_url"], headers=owner.headers)).status_code == 404
    missing = await client.delete(ctx_url, headers=owner.headers)
    assert (missing.status_code, error_code(missing)) == (404, "VOCAB_CONTEXT_NOT_FOUND")
    left = (await client.get(url, headers=owner.headers)).json()
    assert left["contexts"] == [] and len(left["cards"]) == 3

    # F07.06: xóa từ → biến mất cùng thẻ; lưu lại là từ mới với 3 thẻ mới.
    assert (await client.delete(f"{VOCAB}/{manual_id}", headers=owner.headers)).status_code == 204
    assert (await client.get(f"{VOCAB}/{manual_id}", headers=owner.headers)).status_code == 404
    renew = await client.post(VOCAB, json={"term": "学生", "source": "manual"}, headers=owner.headers)
    assert renew.status_code == 201 and renew.json()["entry"]["id"] != manual_id
    assert renew.json()["cards_created"] == 3


async def test_review_session_grading_scheduling_and_card_actions(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-38..44, US-HG-02: thẻ đến hạn, chấm FSRS, chống chấm trùng, tạm ngưng/đặt lại, hoàn thành."""
    clock = FixedClock(datetime.now(timezone.utc))
    app.state.container.clock = clock
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    for term in ("你好", "吗"):
        res = await client.post(VOCAB, json=_save_body(term, bubbles[0], page["id"]), headers=owner.headers)
        assert res.status_code == 201, res.text
    entry = (await client.get(VOCAB, headers=owner.headers)).json()["items"][1]
    await client.patch(f"{VOCAB}/{entry['id']}", json={"note": "mẹo nhớ"}, headers=owner.headers)

    # Chưa có thẻ nào → "no_cards" cho người khác; người học thấy "due".
    nothing = (await client.get(f"{API}/review/summary", headers=other.headers)).json()
    assert (nothing["status"], nothing["total_cards"], nothing["due_now"]) == ("no_cards", 0, 0)
    summary = (await client.get(f"{API}/review/summary", headers=owner.headers)).json()
    assert (summary["status"], summary["due_now"], summary["reviewed_today"]) == ("due", 6, 0)

    # F08.01, F08.03, F08.04: đợt đầu kèm nội dung hai mặt; lọc theo bộ thẻ; người khác không thấy.
    due = (await client.get(f"{API}/cards/due?size=3", headers=owner.headers)).json()
    assert due["total"] == 6 and len(due["items"]) == 3 and due["deck"] == "all"
    card = next(c for c in due["items"] if c["card_type"] == "recognition")
    assert (card["front"]["term"], card["back"]["term"], card["state"]) == (
        card["term"],
        card["term"],
        "learning",
    )
    listening = (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["items"]
    audio = next(c for c in listening if c["card_type"] == "listening")
    assert audio["front"]["term"] is None and audio["front"]["audio_text"] == audio["term"]
    recall = next(c for c in listening if c["card_type"] == "recall")
    assert recall["front"]["term"] is None and recall["back"]["term"] == recall["term"]
    assert (
        card["context"]["snippet_url"].startswith(f"{API}/files/")
        and card["context"]["sentence_zh"] == "你好吗"
    )
    decks = (await client.get(f"{VOCAB}/decks", headers=owner.headers)).json()["items"]
    assert [d["key"] for d in decks] == ["starred", f"series:{page['series_id']}"]
    assert (decks[1]["word_count"], decks[1]["reviewed_count"], decks[1]["due_count"]) == (2, 0, 6)
    by_deck = await client.get(f"{API}/cards/due?deck=series:{page['series_id']}", headers=owner.headers)
    assert by_deck.json()["total"] == 6
    assert (await client.get(f"{API}/cards/due?deck=starred", headers=owner.headers)).json()["total"] == 0
    bad_deck = await client.get(f"{API}/cards/due?deck=series:abc", headers=owner.headers)
    assert (bad_deck.status_code, error_code(bad_deck)) == (400, "INVALID_DECK")
    assert (await client.get(f"{API}/cards/due", headers=other.headers)).json()["total"] == 0

    # F08.02: đánh giá sai → 400; thẻ người khác → 404; "Quên" ngắn hơn "Dễ".
    ids = sorted(c["id"] for c in listening)
    grade_url = f"{API}/cards/{ids[0]}/grade"
    for bad in (0, 5):
        res = await client.post(
            grade_url, json={"rating": bad, "presentation_id": str(uuid.uuid4())}, headers=owner.headers
        )
        assert (res.status_code, error_code(res)) == (400, "INVALID_RATING")
    other_try = await client.post(
        grade_url, json={"rating": 3, "presentation_id": str(uuid.uuid4())}, headers=other.headers
    )
    assert (other_try.status_code, error_code(other_try)) == (404, "CARD_NOT_FOUND")
    presentation = str(uuid.uuid4())
    again = await client.post(
        grade_url, json={"rating": 1, "presentation_id": presentation}, headers=owner.headers
    )
    assert again.status_code == 200, again.text
    forgot = again.json()
    assert forgot["interval_seconds"] == 60 and forgot["remaining_due"] == 5 and not forgot["duplicate"]
    assert forgot["next_card"] is not None and forgot["session_complete"] is False
    assert forgot["card"]["reps"] == 1 and forgot["card"]["state"] == "learning"

    # Bấm đúp cùng presentation_id: trả kết quả cũ, không tính lượt thứ hai.
    twice = await client.post(
        grade_url, json={"rating": 4, "presentation_id": presentation}, headers=owner.headers
    )
    assert twice.json()["duplicate"] is True and twice.json()["due_at"] == forgot["due_at"]
    history = (await client.get(f"{API}/cards/{ids[0]}/history", headers=owner.headers)).json()
    assert history["total"] == 1 and history["items"][0]["rating"] == 1
    assert (await client.get(f"{API}/cards/{ids[0]}/history", headers=other.headers)).status_code == 404
    taken = await client.post(
        f"{API}/cards/{ids[1]}/grade",
        json={"rating": 3, "presentation_id": presentation},
        headers=owner.headers,
    )
    assert (taken.status_code, error_code(taken)) == (409, "PRESENTATION_ID_TAKEN")

    easy = await client.post(
        f"{API}/cards/{ids[1]}/grade",
        json={"rating": 4, "presentation_id": str(uuid.uuid4()), "duration_ms": 1500},
        headers=owner.headers,
    )
    assert (
        easy.json()["interval_seconds"] > forgot["interval_seconds"]
        and easy.json()["card"]["state"] == "review"
    )

    # Thẻ "Quên" quay lại sau 1 phút (giờ giả), thẻ "Dễ" thì không.
    mid = (await client.get(f"{API}/review/summary", headers=owner.headers)).json()
    assert (mid["due_now"], mid["reviewed_today"], mid["status"]) == (4, 2, "due")
    clock.at += timedelta(minutes=2)
    assert (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["total"] == 5

    # F08.05: tạm ngưng loại khỏi đến hạn, chấm thẻ tạm ngưng bị từ chối; tiếp tục; đặt lại giữ lịch sử.
    suspended = await client.post(f"{API}/cards/{ids[2]}/suspend", headers=owner.headers)
    assert suspended.json()["is_suspended"] is True
    assert (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["total"] == 4
    blocked = await client.post(
        f"{API}/cards/{ids[2]}/grade",
        json={"rating": 3, "presentation_id": str(uuid.uuid4())},
        headers=owner.headers,
    )
    assert (blocked.status_code, error_code(blocked)) == (409, "CARD_SUSPENDED")
    assert (await client.post(f"{API}/cards/{ids[2]}/resume", headers=owner.headers)).json()[
        "is_suspended"
    ] is False
    reset = await client.post(f"{API}/cards/{ids[1]}/reset", headers=owner.headers)
    assert (
        reset.json()["reps"] == 0
        and reset.json()["state"] == "learning"
        and reset.json()["stability"] is None
    )
    assert (await client.get(f"{API}/cards/{ids[1]}/history", headers=owner.headers)).json()["total"] == 1
    for action in ("suspend", "resume", "reset"):
        res = await client.post(f"{API}/cards/{ids[0]}/{action}", headers=other.headers)
        assert res.status_code == 404, action

    # F07.03 + F08.01: từ "Đã thuộc"/"Bỏ qua" không có thẻ đến hạn; về "Đang học" thì thẻ trở lại.
    word_id = entry["id"]
    assert (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["total"] == 6
    for status in ("known", "ignored"):
        await client.patch(f"{VOCAB}/{word_id}", json={"status": status}, headers=owner.headers)
        assert (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["total"] == 3
    await client.patch(f"{VOCAB}/{word_id}", json={"status": "learning"}, headers=owner.headers)
    assert (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["total"] == 6

    # Bộ lọc "Cần ôn lại" (due) và số liệu đầu trang theo cùng quy tắc với /cards/due.
    async def due_words(flag: str) -> list[str]:
        res = await client.get(VOCAB, params={"due": flag}, headers=owner.headers)
        body = res.json()
        assert body["total"] == len(body["items"])
        return sorted(i["term"] for i in body["items"])

    async def summary_counts() -> tuple[int, dict[str, int]]:
        body = (await client.get(f"{API}/review/summary", headers=owner.headers)).json()
        return body["due_words"], body["status_counts"]

    assert (await due_words("true"), await due_words("false")) == (["你好", "吗"], [])
    assert await summary_counts() == (2, {"learning": 2, "known": 0, "ignored": 0})
    await client.patch(f"{VOCAB}/{word_id}", json={"status": "known"}, headers=owner.headers)
    assert (await due_words("true"), await due_words("false")) == (["吗"], ["你好"])
    assert await summary_counts() == (1, {"learning": 1, "known": 1, "ignored": 0})
    await client.patch(f"{VOCAB}/{word_id}", json={"status": "learning"}, headers=owner.headers)
    other_id = next(
        i["id"]
        for i in (await client.get(VOCAB, headers=owner.headers)).json()["items"]
        if i["id"] != word_id
    )
    other_cards = (await client.get(f"{VOCAB}/{other_id}", headers=owner.headers)).json()["cards"]
    for c in other_cards:
        await client.post(f"{API}/cards/{c['id']}/suspend", headers=owner.headers)
    assert (len(await due_words("true")), len(await due_words("false"))) == (1, 1)
    assert (await summary_counts())[0] == 1
    for c in other_cards:
        await client.post(f"{API}/cards/{c['id']}/resume", headers=owner.headers)
    assert (await client.get(VOCAB, params={"due": "true", "size": 1}, headers=owner.headers)).json()[
        "total"
    ] == 2
    assert (await client.get(VOCAB, params={"due": "true"}, headers=other.headers)).json()["total"] == 0

    # F08.07: ôn hết thẻ đến hạn → hoàn thành, kèm hạn kế tiếp.
    while True:
        batch = (await client.get(f"{API}/cards/due?size=1", headers=owner.headers)).json()
        if not batch["items"]:
            break
        res = await client.post(
            f"{API}/cards/{batch['items'][0]['id']}/grade",
            json={"rating": 4, "presentation_id": str(uuid.uuid4())},
            headers=owner.headers,
        )
        assert res.status_code == 200
    done = (await client.get(f"{API}/review/summary", headers=owner.headers)).json()
    assert (done["status"], done["due_now"], done["total_cards"]) == ("completed", 0, 6)
    assert done["reviewed_today"] >= 6 and done["next_due_at"] is not None
    assert done["timezone"] == "Asia/Ho_Chi_Minh"
    decks_after = (await client.get(f"{VOCAB}/decks", headers=owner.headers)).json()["items"][1]
    assert decks_after["reviewed_count"] == 2 and decks_after["due_count"] == 0
    finished = (await client.get(f"{VOCAB}?series_id={page['series_id']}", headers=owner.headers)).json()
    assert all(i["is_due"] is False for i in finished["items"])

    # F08.03: từ thiếu nghĩa vẫn đủ 3 thẻ; thẻ recall dùng gợi ý dự phòng và ghi rõ nguồn.
    sound = await client.post(VOCAB, json=_save_body("咚", bubbles[1], page["id"]), headers=owner.headers)
    assert sound.status_code == 201 and sound.json()["cards_created"] == 3, sound.text
    sound_entry = sound.json()["entry"]
    cards = (await client.get(f"{API}/cards/due?size=100", headers=owner.headers)).json()["items"]
    front = next(c for c in cards if c["term"] == "咚" and c["card_type"] == "recall")["front"]
    if sound_entry["meaning_vi"]:
        assert (front["hint_source"], front["meaning_vi"]) == ("meaning", sound_entry["meaning_vi"])
    else:
        # Bong bóng "咚" không có câu dịch nên gợi ý rơi xuống Hán Việt hoặc pinyin, không bao giờ rỗng.
        assert front["hint_source"] in {"sino_vietnamese", "pinyin"}
        assert front[front["hint_source"]]
    recognition = next(c for c in cards if c["term"] == "咚" and c["card_type"] == "recognition")
    assert recognition["front"]["hint_source"] is None
