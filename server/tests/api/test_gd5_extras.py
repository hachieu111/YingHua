"""GĐ5 bổ sung — câu thoại đã lưu (F07.11), lưu tất cả từ của trang (F07.12), cỡ chữ bong bóng (F02.04),
Flashcard AI (F08.11), xóa avatar (F01.10), danh sách giọng (M11), gợi ý truyện và độ phủ từ (F10.04, F10.05).

LLM luôn tắt trong test (xem conftest) nên Flashcard AI trả nội dung dự phòng; dịch vụ ngoài không được gọi.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from app.modules.tts.api.dependencies import get_list_voices
from app.modules.tts.application.use_cases.list_voices import ListVoicesUseCase
from app.modules.tts.domain.errors import TtsUnavailableError
from app.modules.tts.domain.voices import VoiceInfo, make_voice
from tests.api.test_imaging_reader import _drain, _new_page, _worker
from tests.api.test_vocab_review import _ready_page, _save_body
from tests.helpers import Account, error_code, make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"
SENTENCES = f"{API}/saved-sentences"


async def _audit(app: FastAPI, admin_id: int) -> list[str]:
    async with app.state.container.session_factory() as session:
        rows = await session.execute(
            text("SELECT action FROM admin_audit_logs WHERE admin_id = :a ORDER BY id"), {"a": admin_id}
        )
        return [r[0] for r in rows]


# --------------------------------------------------------------------------- F07.11
async def test_saved_sentences_flow_permissions_and_admin(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-70: lưu, trùng 409, danh sách, ghi chú, bỏ lưu; người khác 404; admin xem/xóa có nhật ký."""
    owner, other = await register(client), await register(client)
    admin = await make_admin(app, client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    bubble_id = bubbles[0]["id"]

    assert (await client.post(SENTENCES, json={"bubble_id": bubble_id})).status_code == 401
    saved = await client.post(
        SENTENCES, json={"bubble_id": bubble_id, "note": " ghi chú "}, headers=owner.headers
    )
    assert saved.status_code == 201, saved.text
    body = saved.json()
    assert body["sentence_zh"] == "你好吗" and body["note"] == "ghi chú"
    assert body["pinyin"] == "nǐ hǎo ma" and body["bubble_id"] == bubble_id
    assert body["page_id"] == page["id"] and body["chapter_id"] == page["chapter_id"] and body["page_no"] == 1
    assert body["source_label"] and body["created_at"]
    sentence_id = body["id"]

    dup = await client.post(SENTENCES, json={"bubble_id": bubble_id}, headers=owner.headers)
    assert (dup.status_code, error_code(dup)) == (409, "SENTENCE_ALREADY_SAVED")
    assert dup.json()["error"]["details"]["saved_sentence_id"] == sentence_id
    hidden = await client.post(SENTENCES, json={"bubble_id": bubble_id}, headers=other.headers)
    assert (hidden.status_code, error_code(hidden)) == (404, "BUBBLE_NOT_FOUND")
    long_note = await client.post(
        SENTENCES, json={"bubble_id": bubbles[1]["id"], "note": "x" * 1001}, headers=owner.headers
    )
    assert (long_note.status_code, error_code(long_note)) == (400, "NOTE_TOO_LONG")

    # Bản sửa dịch cá nhân (F05.05) được ưu tiên làm bản dịch của câu.
    await client.put(
        f"{API}/bubbles/{bubbles[1]['id']}/edit", json={"text_vi": "bản sửa"}, headers=owner.headers
    )
    second = await client.post(SENTENCES, json={"bubble_id": bubbles[1]["id"]}, headers=owner.headers)
    assert second.status_code == 201 and second.json()["sentence_vi"] == "bản sửa"

    listing = (await client.get(f"{SENTENCES}?page=1&size=1", headers=owner.headers)).json()
    assert listing["total"] == 2 and listing["items"][0]["id"] == second.json()["id"]  # mới nhất trước
    assert (await client.get(SENTENCES, headers=other.headers)).json()["total"] == 0

    patched = await client.patch(f"{SENTENCES}/{sentence_id}", json={"note": ""}, headers=owner.headers)
    assert patched.status_code == 200 and patched.json()["note"] is None
    foreign = await client.patch(f"{SENTENCES}/{sentence_id}", json={"note": "x"}, headers=other.headers)
    assert (foreign.status_code, error_code(foreign)) == (404, "SAVED_SENTENCE_NOT_FOUND")
    assert (await client.delete(f"{SENTENCES}/{sentence_id}", headers=other.headers)).status_code == 404

    base = f"{API}/admin/users/{owner.id}/saved-sentences"
    assert (await client.get(base, headers=other.headers)).status_code == 403
    admin_list = (await client.get(base, headers=admin.headers)).json()
    assert admin_list["total"] == 2
    assert (await client.delete(f"{base}/{second.json()['id']}", headers=admin.headers)).status_code == 204
    assert "saved_sentence.delete" in await _audit(app, admin.id)

    assert (await client.delete(f"{SENTENCES}/{sentence_id}", headers=owner.headers)).status_code == 204
    assert (await client.delete(f"{SENTENCES}/{sentence_id}", headers=owner.headers)).status_code == 404
    assert (await client.get(SENTENCES, headers=owner.headers)).json()["total"] == 0


async def test_saved_sentence_survives_when_page_is_deleted(app: FastAPI, client: httpx.AsyncClient) -> None:
    """F07.11: câu là bản sao văn bản; trang bị xóa thì nút mở trang gốc ẩn (page_id = null)."""
    owner = await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    await client.post(SENTENCES, json={"bubble_id": bubbles[0]["id"]}, headers=owner.headers)
    assert (await client.delete(f"{API}/pages/{page['id']}", headers=owner.headers)).status_code == 204
    item = (await client.get(SENTENCES, headers=owner.headers)).json()["items"][0]
    assert item["sentence_zh"] == "你好吗" and item["page_id"] is None and item["chapter_id"] is None


# --------------------------------------------------------------------------- F07.12
async def test_save_all_page_words_is_idempotent_and_reports_each_word(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-71: lưu mọi từ chưa có của trang; lặp lại không nhân bản; trang chưa xong → 400."""
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, _ = await _ready_page(client, app, owner)
    url = f"{API}/pages/{page['id']}/save-all-words"
    assert (await client.post(url)).status_code == 401
    assert (await client.post(url, headers=other.headers)).status_code == 404

    first = await client.post(url, headers=owner.headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["saved"] == ["你好"] and body["existing"] == [] and body["failed"] == []
    assert body["skipped"] == ["吗"]  # từ một chữ rất phổ biến không tự lưu
    assert body["remaining"] == 0
    entries = (await client.get(f"{API}/vocab-entries", headers=owner.headers)).json()
    assert entries["total"] == 1 and all(i["source"] == "highlight" for i in entries["items"])
    assert all(i["contexts_count"] == 1 for i in entries["items"])

    again = (await client.post(url, headers=owner.headers)).json()
    assert again["saved"] == [] and again["existing"] == ["你好"] and again["skipped"] == ["吗"]
    assert (await client.get(f"{API}/vocab-entries", headers=owner.headers)).json()["total"] == 1

    pending = await _new_page(client, owner, page["series_id"], page["chapter_id"])
    empty = await client.post(f"{API}/pages/{pending['id']}/save-all-words", headers=owner.headers)
    assert (empty.status_code, error_code(empty)) == (400, "PAGE_HAS_NO_WORDS")


# --------------------------------------------------------------------------- F02.04
async def test_bubble_font_scale_default_valid_steps_and_admin(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-74: mặc định 100; chỉ nhận 80..160 bước 10; admin sửa được và có nhật ký."""
    user = await register(client)
    admin = await make_admin(app, client)
    url = f"{API}/settings"
    assert (await client.get(url, headers=user.headers)).json()["bubble_font_scale"] == 100
    ok = await client.patch(url, json={"bubble_font_scale": 130}, headers=user.headers)
    assert ok.status_code == 200 and ok.json()["bubble_font_scale"] == 130
    for bad in (125, 70, 170, 0):
        res = await client.patch(url, json={"bubble_font_scale": bad}, headers=user.headers)
        assert res.status_code == 400, bad
    assert (await client.get(url, headers=user.headers)).json()["bubble_font_scale"] == 130
    changed = await client.patch(
        f"{API}/admin/users/{user.id}/settings", json={"bubble_font_scale": 90}, headers=admin.headers
    )
    assert changed.status_code == 200 and changed.json()["bubble_font_scale"] == 90
    assert "settings.update" in await _audit(app, admin.id)


# --------------------------------------------------------------------------- F01.10
async def test_remove_avatar_is_idempotent_and_deletes_the_file(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-65: DELETE /account/me/avatar gỡ ảnh đại diện; gọi lại vẫn 204."""
    user = await register(client)
    url = f"{API}/account/me/avatar"
    assert (await client.delete(url)).status_code == 401
    assert (await client.delete(url, headers=user.headers)).status_code == 204  # chưa có ảnh
    up = await client.post(
        url, files={"file": ("a.png", png_bytes((9, 9, 9)), "image/png")}, headers=user.headers
    )
    assert up.status_code == 200 and up.json()["avatar_url"]
    assert (await client.delete(url, headers=user.headers)).status_code == 204
    assert (await client.get(f"{API}/account/me", headers=user.headers)).json()["avatar_url"] is None
    async with app.state.container.session_factory() as session:
        count = await session.scalar(
            text("SELECT count(*) FROM stored_files WHERE kind = 'avatar' AND owner_id = :u"), {"u": user.id}
        )
    assert count == 0
    assert (await client.delete(url, headers=user.headers)).status_code == 204


# --------------------------------------------------------------------------- M11
class _Catalog:
    def __init__(self, voices: list[VoiceInfo] | None) -> None:
        self.voices = voices
        self.calls = 0

    async def list_voices(self) -> list[VoiceInfo]:
        self.calls += 1
        if self.voices is None:
            raise TtsUnavailableError()
        return self.voices


@pytest.fixture
def voices_override(app: FastAPI) -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"catalog": _Catalog([make_voice("zh-CN-XiaoxiaoNeural", "zh-CN", "Female")])}

    def override() -> ListVoicesUseCase:
        container = app.state.container
        return ListVoicesUseCase(state["catalog"], container.voices_cache, container.clock)

    app.dependency_overrides[get_list_voices] = override
    yield state
    app.dependency_overrides.pop(get_list_voices, None)


async def test_tts_voices_from_service_are_cached_and_service_failure_gives_defaults(
    app: FastAPI, client: httpx.AsyncClient, voices_override: dict[str, Any]
) -> None:
    """F11.03: danh sách lưu đệm; dịch vụ lỗi vẫn 200 với danh sách mặc định (không 503)."""
    first = await client.get(f"{API}/tts/voices")
    assert first.status_code == 200
    assert first.json() == {
        "items": [
            {
                "short_name": "zh-CN-XiaoxiaoNeural",
                "locale": "zh-CN",
                "gender": "female",
                "friendly_name": "Xiaoxiao (giọng nữ, Trung Quốc đại lục)",
            }
        ],
        "source": "service",
    }
    await client.get(f"{API}/tts/voices")
    assert voices_override["catalog"].calls == 1  # lần hai lấy từ bộ đệm

    app.state.container.voices_cache = type(app.state.container.voices_cache)(app.state.container.clock)
    voices_override["catalog"] = _Catalog(None)
    failed = await client.get(f"{API}/tts/voices")
    body = failed.json()
    assert failed.status_code == 200 and body["source"] == "default" and len(body["items"]) >= 10
    assert {"short_name", "locale", "gender", "friendly_name"} == set(body["items"][0])


# --------------------------------------------------------------------------- F08.11
async def _save_word(
    client: httpx.AsyncClient, who: Account, page: dict[str, Any], bubble: dict[str, Any]
) -> int:
    saved = await client.post(
        f"{API}/vocab-entries", json=_save_body("你好", bubble, page["id"]), headers=who.headers
    )
    assert saved.status_code == 201, saved.text
    return int(saved.json()["entry"]["id"])


async def test_ai_note_falls_back_caches_limits_regenerate_and_hides_other_users(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-75: LLM tắt → dự phòng (200, không lỗi kỹ thuật), có bộ đệm, Tạo lại bị giới hạn 3 lần."""
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    entry_id = await _save_word(client, owner, page, bubbles[0])
    url = f"{API}/vocab-entries/{entry_id}/ai-note"

    assert (await client.get(url)).status_code == 401
    hidden = await client.get(url, headers=other.headers)
    assert (hidden.status_code, error_code(hidden)) == (404, "VOCAB_NOT_FOUND")

    first = await client.get(url, headers=owner.headers)
    assert first.status_code == 200, first.text
    note = first.json()
    assert note["source"] == "fallback" and note["source_label"] == "Từ từ điển"
    assert note["vocab_entry_id"] == entry_id and note["regenerate_count"] == 0
    assert note["regenerate_remaining"] == 3
    assert isinstance(note["examples"], list) and len(note["examples"]) <= 2
    assert isinstance(note["phrases"], list) and len(note["phrases"]) <= 3
    assert note["mnemonic"] is None or isinstance(note["mnemonic"], str)
    again = (await client.get(url, headers=owner.headers)).json()
    assert again["generated_at"] == note["generated_at"]  # lấy từ bộ đệm, không tạo lại

    for expected in (1, 2, 3):
        res = await client.post(f"{url}/regenerate", headers=owner.headers)
        assert res.status_code == 200 and res.json()["regenerate_count"] == expected
    assert res.json()["regenerate_remaining"] == 0
    limited = await client.post(f"{url}/regenerate", headers=owner.headers)
    assert (limited.status_code, error_code(limited)) == (429, "AI_NOTE_REGENERATE_LIMIT")
    assert (await client.get(url, headers=owner.headers)).json()["regenerate_count"] == 3  # giữ nội dung cũ
    assert (await client.post(f"{url}/regenerate", headers=other.headers)).status_code == 404

    # Xóa mục từ thì thẻ mở rộng đi theo (ON DELETE CASCADE).
    assert (await client.delete(f"{API}/vocab-entries/{entry_id}", headers=owner.headers)).status_code == 204
    async with app.state.container.session_factory() as session:
        left = await session.scalar(
            text("SELECT count(*) FROM vocab_ai_notes WHERE vocab_entry_id = :e"), {"e": entry_id}
        )
    assert left == 0


# --------------------------------------------------------------------------- F10.04, F10.05
async def test_series_recommendations_and_chapter_coverage(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-72, US-NH-73: gợi ý truyện (needs_level khi chưa khai báo) và độ phủ từ vựng của chương."""
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    chapter_url = f"{API}/chapters/{page['chapter_id']}/vocab-coverage"

    assert (await client.get(f"{API}/series/recommendations")).status_code == 401
    assert (
        await client.get(f"{API}/series/recommendations?limit=4", headers=owner.headers)
    ).status_code == 422
    rec = await client.get(f"{API}/series/recommendations", headers=owner.headers)
    assert rec.status_code == 200, rec.text
    assert rec.json()["needs_level"] is True and rec.json()["hsk_level"] is None
    assert isinstance(rec.json()["items"], list) and len(rec.json()["items"]) <= 3

    assert (await client.get(chapter_url)).status_code == 401
    assert (await client.get(chapter_url, headers=other.headers)).status_code == 404
    before = (await client.get(chapter_url, headers=owner.headers)).json()
    assert before["needs_level"] is True and before["hsk_level"] is None
    assert before["status"] in {"ready", "empty"} and before["known_terms"] == 0
    assert before["percent"] == 0 and before["total_terms"] >= 0

    await client.patch(f"{API}/settings", json={"hsk_level": 9}, headers=owner.headers)
    await _save_word(client, owner, page, bubbles[0])
    after = (await client.get(chapter_url, headers=owner.headers)).json()
    assert after["hsk_level"] == 9 and after["needs_level"] is False
    if after["status"] != "empty":
        assert 0 < after["known_terms"] <= after["total_terms"] and 0 < after["percent"] <= 100


async def test_saved_status_reports_only_own_saved_terms_and_sentences(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-31, US-NH-70: dấu "đã lưu" lấy từ máy chủ, đúng sau khi tải lại; không lộ dữ liệu người khác."""
    owner, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    await client.post(f"{API}/pages/{page['id']}/save-all-words", headers=owner.headers)
    await client.post(SENTENCES, json={"bubble_id": bubbles[0]["id"]}, headers=owner.headers)
    url = f"{API}/vocab-entries/saved-status"
    params = [
        ("terms", "你好"),
        ("terms", "朋友"),
        ("bubble_ids", str(bubbles[0]["id"])),
        ("page_id", str(page["id"])),
    ]
    assert (await client.get(url, params=params)).status_code == 401

    mine = (await client.get(url, params=params, headers=owner.headers)).json()
    assert mine == {"terms": ["你好"], "page_terms": ["你好"], "bubble_ids": [bubbles[0]["id"]]}
    theirs = (await client.get(url, params=params, headers=other.headers)).json()
    assert theirs == {"terms": [], "page_terms": [], "bubble_ids": []}
    other_page = [("terms", "你好"), ("page_id", str(page["id"] + 999))]
    elsewhere = (await client.get(url, params=other_page, headers=owner.headers)).json()
    assert (
        elsewhere["terms"] == ["你好"] and elsewhere["page_terms"] == []
    )  # có trong sổ tay nhưng chưa lưu từ trang đó
