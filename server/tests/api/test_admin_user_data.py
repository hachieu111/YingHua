"""M13 F13.07 (US-QT-14) — admin xem/sửa dữ liệu người dùng khác, có nhật ký; người thường bị chặn."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.api.test_imaging_reader import _drain, _worker
from tests.api.test_vocab_review import _ready_page, _save_body
from tests.helpers import Account, error_code, make_admin, register

pytestmark = pytest.mark.integration

API = "/api/v1"


async def _audit(app: FastAPI, admin_id: int) -> list[str]:
    async with app.state.container.session_factory() as session:
        rows = await session.execute(
            text("SELECT action FROM admin_audit_logs WHERE admin_id = :a ORDER BY id"), {"a": admin_id}
        )
        return [r[0] for r in rows]


async def test_admin_views_and_edits_user_data_with_audit_and_guards(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    admin = await make_admin(app, client)
    owner: Account = await register(client)
    stranger = await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, owner)
    saved = await client.post(
        f"{API}/vocab-entries", json=_save_body("你好", bubbles[0], page["id"]), headers=owner.headers
    )
    entry_id = saved.json()["entry"]["id"]
    context_id = saved.json()["entry"]["contexts"][0]["id"]
    base = f"{API}/admin/users/{owner.id}"

    # Người thường → 403; user không tồn tại → 404 USER_NOT_FOUND; chưa đăng nhập → 401.
    forbidden = await client.get(f"{base}/overview", headers=stranger.headers)
    assert forbidden.status_code == 403 and error_code(forbidden) == "PERMISSION_DENIED"
    assert (await client.get(f"{base}/overview")).status_code == 401
    missing = await client.get(f"{API}/admin/users/999999999/overview", headers=admin.headers)
    assert missing.status_code == 404 and error_code(missing) == "USER_NOT_FOUND"
    # Người thường vẫn 404 khi mở tài nguyên của người khác qua API thường.
    other = await client.get(f"{API}/vocab-entries/{entry_id}", headers=stranger.headers)
    assert other.status_code == 404

    # Tổng quan.
    overview = (await client.get(f"{base}/overview", headers=admin.headers)).json()
    assert overview["user"]["id"] == owner.id and "password" not in str(overview)
    assert overview["vocab_counts"]["learning"] == 1 and overview["vocab_total"] == 1
    assert overview["cards_total"] == 3 and overview["cards_due"] == 3
    assert overview["reviews_total"] == 0 and overview["private_series"] == 1

    # Sổ tay.
    listing = (await client.get(f"{base}/vocab-entries", headers=admin.headers)).json()
    assert listing["total"] == 1 and listing["items"][0]["term"] == "你好"
    detail = await client.get(f"{base}/vocab-entries/{entry_id}", headers=admin.headers)
    assert detail.status_code == 200 and len(detail.json()["cards"]) == 3
    patched = await client.patch(
        f"{base}/vocab-entries/{entry_id}",
        json={"note": "admin ghi", "is_starred": True},
        headers=admin.headers,
    )
    assert patched.status_code == 200 and patched.json()["note"] == "admin ghi"
    mine = (await client.get(f"{API}/vocab-entries/{entry_id}", headers=owner.headers)).json()
    assert mine["note"] == "admin ghi" and mine["is_starred"]

    # Thẻ.
    summary = (await client.get(f"{base}/review/summary", headers=admin.headers)).json()
    assert summary["total_cards"] == 3 and summary["status_counts"]["learning"] == 1
    cards = (await client.get(f"{base}/cards", params={"size": 2}, headers=admin.headers)).json()
    assert cards["total"] == 3 and len(cards["items"]) == 2 and cards["items"][0]["term"] == "你好"
    card_id = cards["items"][0]["id"]
    assert (await client.get(f"{base}/cards/{card_id}/history", headers=admin.headers)).status_code == 200
    suspended = await client.post(f"{base}/cards/{card_id}/suspend", headers=admin.headers)
    assert suspended.status_code == 200 and suspended.json()["is_suspended"]
    only = (await client.get(f"{base}/cards", params={"suspended": "true"}, headers=admin.headers)).json()
    assert only["total"] == 1
    assert (await client.post(f"{base}/cards/{card_id}/resume", headers=admin.headers)).status_code == 200
    assert (await client.post(f"{base}/cards/{card_id}/reset", headers=admin.headers)).status_code == 200
    bad = await client.get(f"{base}/cards", params={"state": "x"}, headers=admin.headers)
    assert bad.status_code == 400 and error_code(bad) == "INVALID_CARD_STATE"

    # Cài đặt.
    changed = await client.patch(f"{base}/settings", json={"hsk_level": 3}, headers=admin.headers)
    assert changed.status_code == 200 and changed.json()["hsk_level"] == 3
    assert (await client.get(f"{API}/settings", headers=owner.headers)).json()["hsk_level"] == 3
    assert (await client.get(f"{base}/settings", headers=admin.headers)).json()["hsk_level"] == 3

    # Đọc truyện: ghi chú, dấu trang, bản sửa dịch.
    pid, bubble_id = page["id"], bubbles[0]["id"]
    await client.put(f"{API}/pages/{pid}/bookmark", json={"is_bookmarked": True}, headers=owner.headers)
    await client.put(f"{API}/bubbles/{bubble_id}/edit", json={"text_vi": "bản sửa"}, headers=owner.headers)
    marks = (await client.get(f"{base}/bookmarks", headers=admin.headers)).json()
    assert marks["total"] == 1
    edits = (await client.get(f"{base}/bubble-edits", params={"page_id": pid}, headers=admin.headers)).json()
    assert [e["bubble_id"] for e in edits] == [bubble_id] and edits[0]["has_edit"]
    body = {"highlights": {str(bubble_id): "#ffcc00"}, "strokes": []}
    put = await client.put(f"{base}/pages/{pid}/annotations", json=body, headers=admin.headers)
    assert put.status_code == 200, put.text
    got = (await client.get(f"{base}/pages/{pid}/annotations", headers=admin.headers)).json()
    assert got["is_bookmarked"] and got["highlights"]
    assert (await client.delete(f"{base}/pages/{pid}/annotations", headers=admin.headers)).status_code == 204
    assert (await client.delete(f"{base}/bubbles/{bubble_id}/edit", headers=admin.headers)).status_code == 204
    gone = (await client.get(f"{base}/bubble-edits", params={"page_id": pid}, headers=admin.headers)).json()
    assert gone == []

    # Xóa ngữ cảnh rồi xóa từ.
    ctx = await client.delete(f"{base}/vocab-entries/{entry_id}/contexts/{context_id}", headers=admin.headers)
    assert ctx.status_code == 204
    assert (await client.delete(f"{base}/vocab-entries/{entry_id}", headers=admin.headers)).status_code == 204
    assert (await client.get(f"{API}/vocab-entries/{entry_id}", headers=owner.headers)).status_code == 404

    actions = await _audit(app, admin.id)
    assert actions == [
        "vocab.update",
        "card.suspend",
        "card.resume",
        "card.reset",
        "settings.update",
        "user_data.annotation.update",
        "user_data.annotation.delete",
        "user_data.bubble_edit.delete",
        "vocab.context_delete",
        "vocab.delete",
    ]
