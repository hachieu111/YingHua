"""GĐ6 đợt A2 — cấu hình hệ thống, kiểm duyệt, nhật ký, ghi nhớ đăng nhập, ảnh đại diện có sẵn, trang mẫu.

Mã: F13.04–F13.06, F01.10, F01.11, F04.16 (US-QT-12, US-QT-13, US-NH-65, US-NH-76, US-NH-77).
Cấu hình hệ thống là dữ liệu dùng chung nên mỗi test dọn các khóa nó đã đặt.
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.helpers import Account, error_code, make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"
TOUCHED_KEYS = (
    "grammar_daily_limit",
    "admin_notifications_enabled",
    "auto_moderation_enabled",
    "sample_page_id",
)


@pytest.fixture
async def clean_settings(app: FastAPI, client: httpx.AsyncClient) -> AsyncIterator[None]:
    async def wipe() -> None:
        async with app.state.container.session_factory() as session:
            await session.execute(
                text("DELETE FROM system_settings WHERE key = ANY(:keys)"), {"keys": list(TOUCHED_KEYS)}
            )
            await session.commit()
        app.state.container.system_settings.invalidate()

    await wipe()
    yield
    await wipe()


def _color() -> tuple[int, int, int]:
    return random.randrange(256), random.randrange(256), random.randrange(256)


async def _upload_page(client: httpx.AsyncClient, who: Account) -> tuple[int, int]:
    """Tải một ảnh nhỏ vào chương riêng; trả (page_id, file_id)."""
    series = (await client.post(f"{API}/series", json={"title_vi": "Kiểm duyệt"}, headers=who.headers)).json()
    chapter = (
        await client.post(f"{API}/series/{series['id']}/chapters", json={"number": 1}, headers=who.headers)
    ).json()
    up = await client.post(
        f"{API}/chapters/{chapter['id']}/pages",
        files=[("files", ("p.png", png_bytes(_color()), "application/octet-stream"))],
        headers=who.headers,
    )
    assert up.status_code == 201, up.text
    page_id = int(up.json()["results"][0]["page"]["id"])
    reading = (await client.get(f"{API}/pages/{page_id}/reading", headers=who.headers)).json()
    return page_id, int(reading["variants"]["original"].rsplit("/", 1)[1])


# ---- F13.05 cấu hình hệ thống -------------------------------------------------------------------


async def test_system_settings_admin_only_validate_update_and_audit(
    app: FastAPI, client: httpx.AsyncClient, clean_settings: None
) -> None:
    """US-QT-13 TC4, TC10: kiểm giá trị, có hiệu lực ngay, ghi nhật ký; người học bị chặn."""
    admin, learner = await make_admin(app, client), await register(client)
    assert (await client.get(f"{API}/admin/system-settings", headers=learner.headers)).status_code == 403
    assert (
        await client.patch(f"{API}/admin/system-settings", json={}, headers=learner.headers)
    ).status_code == 403

    first = (await client.get(f"{API}/admin/system-settings", headers=admin.headers)).json()
    assert first["values"]["maintenance_mode"] is False and "grammar_daily_limit" not in first["overridden"]

    for bad in ({"grammar_daily_limit": -1}, {"grammar_daily_limit": "abc"}, {"khong_co": 1}):
        res = await client.patch(f"{API}/admin/system-settings", json=bad, headers=admin.headers)
        assert res.status_code == 400, res.text
    assert error_code(await client.patch(f"{API}/admin/system-settings", json={}, headers=admin.headers)) == (
        "EMPTY_SETTINGS_CHANGE"
    )

    res = await client.patch(
        f"{API}/admin/system-settings",
        json={"grammar_daily_limit": 7, "admin_notifications_enabled": False},
        headers=admin.headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert (
        body["values"]["grammar_daily_limit"] == 7 and body["values"]["admin_notifications_enabled"] is False
    )
    assert {"grammar_daily_limit", "admin_notifications_enabled"} <= set(body["overridden"])
    again = (await client.get(f"{API}/admin/system-settings", headers=admin.headers)).json()
    assert again["values"]["grammar_daily_limit"] == 7

    logs = await client.get(
        f"{API}/admin/audit-logs",
        params={"action": "settings.updated", "admin_id": admin.id},
        headers=admin.headers,
    )
    assert logs.status_code == 200 and logs.json()["total"] >= 1
    item = logs.json()["items"][0]
    assert item["admin"]["id"] == admin.id and item["details"]["changes"]["grammar_daily_limit"]["to"] == 7

    reset = await client.patch(
        f"{API}/admin/system-settings", json={"grammar_daily_limit": None}, headers=admin.headers
    )
    assert reset.status_code == 200, reset.text
    assert "grammar_daily_limit" not in reset.json()["overridden"]
    assert reset.json()["values"]["grammar_daily_limit"] == app.state.container.settings.grammar_daily_limit
    assert "admin_notifications_enabled" in reset.json()["overridden"]


async def test_public_system_status_needs_no_login_and_hides_internal_limits(
    client: httpx.AsyncClient,
) -> None:
    """US-QT-13 TC3, TC5: giao diện đọc trạng thái bảo trì/LLM/TTS từ API."""
    res = await client.get(f"{API}/system/status")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"maintenance_mode", "message", "llm_enabled", "tts_enabled", "sample_page_available"}


# ---- F13.04 kiểm duyệt --------------------------------------------------------------------------


async def test_moderation_queue_flags_remove_with_reason_and_files_become_unavailable(
    app: FastAPI, client: httpx.AsyncClient, clean_settings: None
) -> None:
    """US-QT-12 TC1–TC4: hàng chờ kèm người tải, gỡ cần lý do, ảnh không còn phục vụ, có nhật ký."""
    admin, owner = await make_admin(app, client), await register(client)
    page_id, file_id = await _upload_page(client, owner)

    queue = await client.get(f"{API}/admin/moderation/uploads", params={"size": 100}, headers=admin.headers)
    assert queue.status_code == 200, queue.text
    mine = next(i for i in queue.json()["items"] if i["file_id"] == file_id)
    assert mine["uploader"]["id"] == owner.id and mine["page_id"] == page_id
    assert "tiny_image" in mine["flags"]  # ảnh thử chỉ 24x36 px
    flagged = await client.get(
        f"{API}/admin/moderation/uploads", params={"flagged_only": True, "size": 100}, headers=admin.headers
    )
    assert any(i["file_id"] == file_id for i in flagged.json()["items"])

    # Tắt kiểm duyệt tự động: không gắn cờ, bộ lọc cờ rỗng (US-QT-13 TC6).
    off = await client.patch(
        f"{API}/admin/system-settings", json={"auto_moderation_enabled": False}, headers=admin.headers
    )
    assert off.status_code == 200
    plain = await client.get(f"{API}/admin/moderation/uploads", params={"size": 100}, headers=admin.headers)
    assert next(i for i in plain.json()["items"] if i["file_id"] == file_id)["flags"] == []
    only = await client.get(
        f"{API}/admin/moderation/uploads", params={"flagged_only": True}, headers=admin.headers
    )
    assert only.json() == {"items": [], "total": 0, "page": 1, "size": 20}

    # Người học bị chặn; thiếu lý do hoặc chỉ định sai thì từ chối.
    denied = await client.post(
        f"{API}/admin/moderation/removals", json={"page_id": page_id, "reason": "x"}, headers=owner.headers
    )
    assert denied.status_code == 403
    no_reason = await client.post(
        f"{API}/admin/moderation/removals", json={"page_id": page_id}, headers=admin.headers
    )
    assert no_reason.status_code == 400 and error_code(no_reason) == "REMOVAL_REASON_REQUIRED"
    both = await client.post(
        f"{API}/admin/moderation/removals",
        json={"page_id": page_id, "file_id": file_id, "reason": "x"},
        headers=admin.headers,
    )
    assert error_code(both) == "REMOVAL_TARGET_INVALID"
    missing = await client.post(
        f"{API}/admin/moderation/removals", json={"page_id": 999999999, "reason": "x"}, headers=admin.headers
    )
    assert missing.status_code == 404

    assert (await client.get(f"{API}/files/{file_id}", headers=owner.headers)).status_code == 200
    done = await client.post(
        f"{API}/admin/moderation/removals",
        json={"page_id": page_id, "reason": "Ảnh vi phạm"},
        headers=admin.headers,
    )
    assert done.status_code == 201, done.text
    assert done.json()["reason"] == "Ảnh vi phạm" and done.json()["owner"]["id"] == owner.id
    assert done.json()["removed_by"]["id"] == admin.id
    assert (await client.get(f"{API}/files/{file_id}", headers=owner.headers)).status_code == 404
    again = await client.post(
        f"{API}/admin/moderation/removals", json={"file_id": file_id, "reason": "lại"}, headers=admin.headers
    )
    assert again.status_code == 409 and error_code(again) == "ALREADY_REMOVED"

    removals = await client.get(f"{API}/admin/moderation/removals", headers=admin.headers)
    assert removals.json()["items"][0]["file_id"] == file_id
    after = await client.get(f"{API}/admin/moderation/uploads", params={"size": 100}, headers=admin.headers)
    assert all(i["file_id"] != file_id for i in after.json()["items"])
    logs = await client.get(
        f"{API}/admin/audit-logs", params={"action": "content.removed"}, headers=admin.headers
    )
    assert logs.json()["items"][0]["details"]["reason"] == "Ảnh vi phạm"

    # F13.04 bước 4, F14.05: chủ ảnh nhận thông báo kèm lý do và mã trang.
    inbox = (await client.get(f"{API}/notifications", headers=owner.headers)).json()
    note = next(n for n in inbox["items"] if n["kind"] == "content_removed")
    assert "Ảnh vi phạm" in note["body"] and note["data"] == {"page_id": page_id} and note["is_read"] is False


async def test_changed_ai_limit_takes_effect_for_reader_policy(
    app: FastAPI, client: httpx.AsyncClient, clean_settings: None
) -> None:
    """US-QT-13 TC10, F13.05: hạn mức ngữ pháp do quản trị đặt là hạn mức chính sách AI đọc được ngay."""
    from app.modules.admin.application.public import grammar_ai_policy, mistake_review_ai_policy

    admin = await make_admin(app, client)
    settings = app.state.container.system_settings
    default = (
        await grammar_ai_policy(settings).daily_limit(admin.id),
        await mistake_review_ai_policy(settings).daily_limit(admin.id),
    )
    assert default == (
        app.state.container.settings.grammar_daily_limit,
        app.state.container.settings.mistake_review_daily_limit,
    )
    res = await client.patch(
        f"{API}/admin/system-settings", json={"grammar_daily_limit": 3}, headers=admin.headers
    )
    assert res.status_code == 200, res.text
    assert await grammar_ai_policy(settings).daily_limit(admin.id) == 3
    assert await mistake_review_ai_policy(settings).daily_limit(admin.id) == default[1]


async def test_audit_logs_filter_by_admin_target_and_time(app: FastAPI, client: httpx.AsyncClient) -> None:
    """F13.06: xem, lọc, phân trang; không có thao tác sửa hay xóa."""
    admin, other_admin, target = (
        await make_admin(app, client),
        await make_admin(app, client),
        await register(client),
    )
    await client.post(f"{API}/admin/users/{target.id}/lock", json={"reason": "thử"}, headers=admin.headers)
    res = await client.get(
        f"{API}/admin/audit-logs",
        params={"admin_id": admin.id, "target_type": "user", "since": "2020-01-01T00:00:00Z"},
        headers=admin.headers,
    )
    assert res.status_code == 200
    assert [i["action"] for i in res.json()["items"]] == ["user.locked"]
    none = await client.get(
        f"{API}/admin/audit-logs", params={"admin_id": other_admin.id}, headers=admin.headers
    )
    assert none.json()["total"] == 0
    future = datetime(2100, 1, 1, tzinfo=timezone.utc).isoformat()
    empty = await client.get(f"{API}/admin/audit-logs", params={"since": future}, headers=admin.headers)
    assert empty.json()["items"] == []
    bystander = await register(client)
    assert (await client.get(f"{API}/admin/audit-logs", headers=bystander.headers)).status_code == 403
    assert (await client.delete(f"{API}/admin/audit-logs", headers=admin.headers)).status_code == 405


# ---- F01.11 ghi nhớ đăng nhập -------------------------------------------------------------------


async def _session_lifetime_days(app: FastAPI, user_id: int) -> float:
    async with app.state.container.session_factory() as session:
        row = await session.execute(
            text(
                "SELECT EXTRACT(EPOCH FROM (expires_at - created_at)) / 86400 FROM refresh_tokens "
                "WHERE user_id = :u AND replaced_by_id IS NULL AND revoked_at IS NULL "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"u": user_id},
        )
        return float(row.scalar_one())


async def test_login_without_remember_me_gives_short_session_that_survives_refresh(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-76 TC1, TC2, TC4: phiên ngắn không đổi thành phiên dài khi làm mới."""
    account = await register(client)
    default = await client.post(
        f"{API}/auth/login", json={"email": account.email, "password": account.password}
    )
    assert default.json()["tokens"]["remember_me"] is True
    assert round(await _session_lifetime_days(app, account.id)) == 30

    short = await client.post(
        f"{API}/auth/login", json={"email": account.email, "password": account.password, "remember_me": False}
    )
    assert short.status_code == 200 and short.json()["tokens"]["remember_me"] is False
    assert round(await _session_lifetime_days(app, account.id), 2) == 1.0

    refreshed = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": short.json()["tokens"]["refresh_token"]}
    )
    assert refreshed.status_code == 200 and refreshed.json()["tokens"]["remember_me"] is False
    assert round(await _session_lifetime_days(app, account.id), 2) == 1.0


# ---- F01.10 ảnh đại diện có sẵn -----------------------------------------------------------------


async def test_avatar_preset_and_upload_are_mutually_exclusive(client: httpx.AsyncClient) -> None:
    """US-NH-65 TC6: chọn ảnh có sẵn gỡ ảnh tải lên và ngược lại."""
    who = await register(client)
    listing = await client.get(f"{API}/account/avatar-presets", headers=who.headers)
    codes = [i["code"] for i in listing.json()["items"]]
    assert "sakura_flower" in codes

    bad = await client.put(
        f"{API}/account/me/avatar-preset", json={"preset": "khong-co"}, headers=who.headers
    )
    assert bad.status_code == 400 and error_code(bad) == "INVALID_AVATAR_PRESET"

    up = await client.post(
        f"{API}/account/me/avatar",
        files={"file": ("a.png", png_bytes(_color()), "image/png")},
        headers=who.headers,
    )
    assert up.json()["avatar_url"] and up.json()["avatar_preset"] is None
    old_url = up.json()["avatar_url"]

    chosen = await client.put(
        f"{API}/account/me/avatar-preset", json={"preset": "mac_van"}, headers=who.headers
    )
    assert chosen.status_code == 200
    assert chosen.json()["avatar_preset"] == "mac_van" and chosen.json()["avatar_url"] is None
    assert (await client.get(old_url, headers=who.headers)).status_code == 404
    me = await client.get(f"{API}/account/me", headers=who.headers)
    assert me.json()["avatar_preset"] == "mac_van"

    again = await client.post(
        f"{API}/account/me/avatar",
        files={"file": ("b.png", png_bytes(_color()), "image/png")},
        headers=who.headers,
    )
    assert again.json()["avatar_preset"] is None and again.json()["avatar_url"]

    await client.put(f"{API}/account/me/avatar-preset", json={"preset": "lac_ly"}, headers=who.headers)
    assert (await client.delete(f"{API}/account/me/avatar", headers=who.headers)).status_code == 204
    final = (await client.get(f"{API}/account/me", headers=who.headers)).json()
    assert final["avatar_preset"] is None and final["avatar_url"] is None


# ---- F04.16 trang mẫu ---------------------------------------------------------------------------


async def test_sample_page_not_configured_and_invalid_choice_are_rejected(
    app: FastAPI, client: httpx.AsyncClient, clean_settings: None
) -> None:
    """US-NH-77 TC5: chưa có trang mẫu → 404; quản trị chỉ chọn được trang công khai đã dịch xong."""
    admin, learner = await make_admin(app, client), await register(client)
    assert (await client.get(f"{API}/sample-page")).status_code == 401
    missing = await client.get(f"{API}/sample-page", headers=learner.headers)
    assert missing.status_code == 404 and error_code(missing) == "SAMPLE_PAGE_NOT_CONFIGURED"

    page_id, _ = await _upload_page(client, learner)  # trang riêng tư, chưa dịch
    bad = await client.patch(
        f"{API}/admin/system-settings", json={"sample_page_id": page_id}, headers=admin.headers
    )
    assert bad.status_code == 400 and error_code(bad) == "SAMPLE_PAGE_INVALID"
    assert (await client.get(f"{API}/system/status")).json()["sample_page_available"] is False


async def test_sample_page_candidates_list_only_public_done_pages(
    app: FastAPI, client: httpx.AsyncClient, clean_settings: None
) -> None:
    """US-QT-13 TC13: ô chọn trang mẫu chỉ có trang công khai đã dịch xong, và chọn được ngay."""
    admin, learner = await make_admin(app, client), await register(client)
    url = f"{API}/admin/system-settings/sample-page-candidates"
    assert (await client.get(url, headers=learner.headers)).status_code == 403

    private_page, _ = await _upload_page(client, learner)
    public_page, _ = await _upload_page(client, admin)
    async with app.state.container.session_factory() as session:
        await session.execute(
            text(
                "UPDATE series SET visibility = 'public', owner_id = NULL WHERE id = "
                "(SELECT c.series_id FROM pages p JOIN chapters c ON c.id = p.chapter_id WHERE p.id = :id)"
            ),
            {"id": public_page},
        )
        await session.execute(
            text(
                "UPDATE translations SET status = 'done' "
                "WHERE id = (SELECT translation_id FROM pages WHERE id = :id)"
            ),
            {"id": public_page},
        )
        await session.commit()

    items = (await client.get(url, headers=admin.headers)).json()["items"]
    ids = [item["page_id"] for item in items]
    assert public_page in ids and private_page not in ids
    chosen = next(item for item in items if item["page_id"] == public_page)
    assert chosen["series_title"] == "Kiểm duyệt" and chosen["page_no"] == 1 and chosen["bubble_count"] == 0
    saved = await client.patch(
        f"{API}/admin/system-settings", json={"sample_page_id": public_page}, headers=admin.headers
    )
    assert saved.status_code == 200 and saved.json()["values"]["sample_page_id"] == public_page
