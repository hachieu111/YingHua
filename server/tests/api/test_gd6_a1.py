"""Đợt A1 giai đoạn 6 — M12 Thống kê, M14 Báo lỗi/Thông báo/Nhắc ôn, F07.08 Xuất sổ tay.

US-NH-56..60, US-QT-08, US-QT-11, US-HG-04. Bong bóng dựng bằng worker giả như test sổ tay.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from app.modules.jobs.infrastructure.tasks import build_job_tasks
from tests.api.test_imaging_reader import _drain, _worker
from tests.api.test_vocab_review import VOCAB, _ready_page, _save_body
from tests.conftest import FixedClock
from tests.helpers import Account, error_code, make_admin, register

pytestmark = pytest.mark.integration

API = "/api/v1"


async def _save_and_grade(client: httpx.AsyncClient, app: FastAPI, who: Account) -> tuple[dict, dict, dict]:
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, who)
    saved = await client.post(VOCAB, json=_save_body("你好", bubbles[0], page["id"]), headers=who.headers)
    assert saved.status_code == 201, saved.text
    card_id = saved.json()["entry"]["cards"][0]["id"]
    graded = await client.post(
        f"{API}/cards/{card_id}/grade",
        json={"rating": 3, "presentation_id": str(uuid.uuid4()), "duration_ms": 4200},
        headers=who.headers,
    )
    assert graded.status_code == 200, graded.text
    return page, bubbles[0], saved.json()


async def test_stats_record_activity_in_same_transaction_and_report_streak(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-56 TC1-4, US-NH-57 TC1,3,4: số liệu, tỉ lệ nhớ, chuỗi ngày, tiến độ đọc, phân quyền."""
    fresh = await register(client)
    empty = (await client.get(f"{API}/stats/overview", headers=fresh.headers)).json()
    assert empty["words_total"] == 0 and empty["retention_rate"] is None  # TC3: không chia cho 0
    streak0 = (await client.get(f"{API}/stats/streak", headers=fresh.headers)).json()
    assert streak0["current_streak"] == 0 and streak0["reading"] == [] and streak0["reading_hint"]  # TC4

    owner = await register(client)
    page, _, _ = await _save_and_grade(client, app, owner)
    chapter_id = (await client.get(f"{API}/pages/{page['id']}", headers=owner.headers)).json()["chapter_id"]
    progress = await client.put(
        f"{API}/chapters/{chapter_id}/progress", json={"page_no": 1}, headers=owner.headers
    )
    assert progress.status_code == 200, progress.text

    overview = (await client.get(f"{API}/stats/overview", headers=owner.headers)).json()
    assert overview["words_total"] == 1 and overview["reviews_total"] == 1
    assert overview["retention_rate"] == 1.0 and overview["pages_read_total"] == 1
    assert overview["study_seconds_total"] == 4 and overview["cards_total"] == 3

    activity = (
        await client.get(f"{API}/stats/activity?granularity=day&count=7", headers=owner.headers)
    ).json()
    today = activity["points"][-1]
    assert (today["words_saved"], today["reviews_count"], today["pages_read"]) == (1, 1, 1)
    assert activity["current_week"]["reviews_count"] == 1 and activity["delta"]["reviews_count"] == 1
    for granularity in ("week", "month"):
        res = await client.get(
            f"{API}/stats/activity?granularity={granularity}&count=3", headers=owner.headers
        )
        assert res.status_code == 200 and len(res.json()["points"]) == 3
    bad = await client.get(f"{API}/stats/activity?granularity=year", headers=owner.headers)
    assert (bad.status_code, error_code(bad)) == (400, "INVALID_INPUT")

    streak = (await client.get(f"{API}/stats/streak", headers=owner.headers)).json()
    assert streak["current_streak"] == 1 and streak["longest_streak"] == 1 and streak["studied_today"] is True
    assert streak["week"][-1]["studied"] is True and streak["rule"]
    assert streak["reading"][0]["pages_read"] == 1 and streak["reading"][0]["pages_total"] >= 1

    # Lưu thêm một từ nữa: số từ tăng đúng một (TC2).
    again = await client.post(VOCAB, json=_save_body("朋友"), headers=owner.headers)
    assert again.status_code == 201
    assert (await client.get(f"{API}/stats/overview", headers=owner.headers)).json()["words_total"] == 2

    # Chỉ dữ liệu của chính mình; khách → 401; người thường vào API quản trị → 403.
    assert (await client.get(f"{API}/stats/overview", headers=fresh.headers)).json()["words_total"] == 0
    assert (await client.get(f"{API}/stats/overview")).status_code == 401
    assert (
        await client.get(f"{API}/admin/users/{owner.id}/stats/overview", headers=fresh.headers)
    ).status_code == 403
    admin = await make_admin(app, client)
    view = await client.get(f"{API}/admin/users/{owner.id}/stats/overview", headers=admin.headers)
    assert view.status_code == 200 and view.json()["words_total"] == 2


async def test_system_stats_admin_only(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-QT-08: số liệu tổng hợp cho quản trị viên, người học bị từ chối."""
    user = await register(client)
    admin = await make_admin(app, client)
    assert (await client.get(f"{API}/admin/stats", headers=user.headers)).status_code == 403
    stats = (await client.get(f"{API}/admin/stats", headers=admin.headers)).json()
    assert stats["users"]["total"] >= 2 and stats["users"]["admins"] >= 1
    assert set(stats["imaging"]) >= {"pages_done", "pages_failed", "ocr_success_rate", "ocr_failure_rate"}
    assert stats["activity_7_days"]["active_users"] >= 0 and "words_saved_total" in stats


async def test_error_report_flow_duplicate_resolve_and_notification(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-58 TC1-4, US-QT-11 TC1,2,4, F14.05: báo lỗi, chống trùng, xử lý, thông báo cho người báo."""
    reporter, other = await register(client), await register(client)
    await _drain(_worker(app))
    page, bubbles = await _ready_page(client, app, reporter)
    url = f"{API}/error-reports"
    body = {"page_id": page["id"], "bubble_id": bubbles[0]["id"], "report_type": "translation"}

    empty = await client.post(url, json={"page_id": page["id"]}, headers=reporter.headers)
    assert (empty.status_code, error_code(empty)) == (400, "REPORT_CONTENT_REQUIRED")  # TC2
    created = await client.post(url, json={**body, "description": "Dịch sai"}, headers=reporter.headers)
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["status"] == "new" and report["bubble_text_zh"] == "你好吗" and report["page_no"] == 1
    dup = await client.post(url, json=body, headers=reporter.headers)
    assert (dup.status_code, error_code(dup)) == (409, "REPORT_ALREADY_EXISTS")  # TC3
    assert dup.json()["error"]["details"]["report_id"] == report["id"]
    hidden = await client.post(url, json=body, headers=other.headers)  # trang riêng tư của người khác
    assert hidden.status_code == 404

    admin = await make_admin(app, client)
    admin_url = f"{API}/admin/error-reports"
    assert (await client.get(admin_url, headers=reporter.headers)).status_code == 403  # TC4
    listing = (
        await client.get(f"{admin_url}?status=new&reporter_id={reporter.id}", headers=admin.headers)
    ).json()
    assert listing["total"] == 1 and listing["items"][0]["reporter"]["id"] == reporter.id
    assert (await client.get(f"{admin_url}?status=bogus", headers=admin.headers)).status_code == 400

    bad = await client.patch(f"{admin_url}/{report['id']}", json={"status": "new"}, headers=admin.headers)
    assert bad.status_code == 422
    done = await client.patch(
        f"{admin_url}/{report['id']}", json={"status": "resolved", "note": "Đã sửa"}, headers=admin.headers
    )
    assert done.status_code == 200 and done.json()["status"] == "resolved"
    again = await client.patch(
        f"{admin_url}/{report['id']}", json={"status": "rejected"}, headers=admin.headers
    )
    assert (again.status_code, error_code(again)) == (409, "REPORT_ALREADY_HANDLED")

    mine = (await client.get(url, headers=reporter.headers)).json()
    assert mine["items"][0]["status"] == "resolved" and mine["items"][0]["resolution_note"] == "Đã sửa"
    assert (await client.get(f"{API}/notifications/unread-count", headers=reporter.headers)).json() == {
        "unread": 1
    }
    inbox = (await client.get(f"{API}/notifications", headers=reporter.headers)).json()
    note = inbox["items"][0]
    assert note["kind"] == "report_resolved" and note["is_read"] is False and inbox["unread"] == 1
    assert (
        await client.post(f"{API}/notifications/{note['id']}/read", headers=other.headers)
    ).status_code == 404
    read = await client.post(f"{API}/notifications/{note['id']}/read", headers=reporter.headers)
    assert read.json() == {"unread": 0}
    assert (await client.post(f"{API}/notifications/read-all", headers=reporter.headers)).json()[
        "updated"
    ] == 0
    async with app.state.container.session_factory() as session:
        count = (
            await session.execute(
                text(
                    "SELECT count(*) FROM admin_audit_logs "
                    "WHERE action = 'error_report.resolved' AND target_id = :i"
                ),
                {"i": report["id"]},
            )
        ).scalar_one()
    assert count == 1


async def test_reminder_settings_and_scheduled_reminder_sent_once(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-59, US-HG-04: cấu hình giờ nhắc, chỉ nhắc khi còn thẻ đến hạn, tối đa một lời nhắc mỗi ngày."""
    user = await register(client)
    bad = await client.patch(f"{API}/settings", json={"reminder_time": "25:00"}, headers=user.headers)
    assert (bad.status_code, error_code(bad)) == (400, "INVALID_INPUT")
    needs_time = await client.patch(f"{API}/settings", json={"reminder_enabled": True}, headers=user.headers)
    assert needs_time.status_code == 400
    ok = await client.patch(
        f"{API}/settings", json={"reminder_enabled": True, "reminder_time": "08:30"}, headers=user.headers
    )
    assert ok.status_code == 200 and ok.json()["reminder_time"] == "08:30" and ok.json()["reminder_enabled"]

    container = app.state.container
    tasks = build_job_tasks(
        container.session_factory,
        container.storage,
        FixedClock(datetime.now(timezone.utc)),
        container.settings,
    )
    reminders = tasks["send_reminders"]
    local = datetime(2026, 10, 26, 8, 40, tzinfo=timezone(timedelta(hours=7)))
    now = local.astimezone(timezone.utc)

    first = await reminders.run(now)  # chưa có thẻ nào -> không nhắc (TC2)
    assert first["sent"] == 0
    await _save_and_grade(client, app, user)  # tạo thẻ; 2 thẻ còn lại đến hạn (thẻ đã chấm được dời)
    await client.post(VOCAB, json=_save_body("朋友"), headers=user.headers)
    early = await reminders.run(datetime(2026, 10, 26, 1, 0, tzinfo=timezone.utc))  # 08:00 giờ VN
    assert early["sent"] == 0 and early["skipped_not_due_time"] >= 1
    # Chạy tại giờ nhắc hợp lệ của một ngày sau đó, khi chắc chắn có thẻ đến hạn.
    day2 = datetime(2026, 11, 20, 1, 40, tzinfo=timezone.utc)  # 08:40 giờ VN
    first_day2 = await reminders.run(day2)
    second_day2 = await reminders.run(day2 + timedelta(minutes=15))
    assert first_day2["sent"] >= 1 and second_day2["sent"] == 0 and second_day2["skipped_already"] >= 1
    inbox = (await client.get(f"{API}/notifications?unread_only=true", headers=user.headers)).json()
    reminder = [n for n in inbox["items"] if n["kind"] == "reminder"]
    assert reminder and "thẻ" in reminder[0]["title"] and reminder[0]["data"]["due_cards"] >= 1

    off = await client.patch(f"{API}/settings", json={"reminder_enabled": False}, headers=user.headers)
    assert off.status_code == 200
    day3 = datetime(2026, 11, 21, 1, 40, tzinfo=timezone.utc)
    await reminders.run(day3)
    after = (await client.get(f"{API}/notifications", headers=user.headers)).json()
    assert sum(1 for n in after["items"] if n["kind"] == "reminder") == len(reminder)  # TC3: đã tắt


async def test_export_vocab_csv_and_anki(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-60: CSV có BOM, tệp Anki, bộ lọc, sổ tay trống, phân quyền."""
    user, other = await register(client), await register(client)
    empty = await client.get(f"{VOCAB}/export?format=csv", headers=user.headers)
    assert (empty.status_code, error_code(empty)) == (404, "VOCAB_EXPORT_EMPTY")  # TC3
    assert (await client.get(f"{VOCAB}/export?format=csv")).status_code == 401

    for term in ("你好", "朋友"):
        assert (await client.post(VOCAB, json=_save_body(term), headers=user.headers)).status_code == 201
    entry = (await client.get(f"{VOCAB}?q=朋友", headers=user.headers)).json()["items"][0]
    await client.patch(
        f"{VOCAB}/{entry['id']}", json={"status": "known", "note": "=HYPERLINK(1)"}, headers=user.headers
    )

    csv_res = await client.get(f"{VOCAB}/export?format=csv", headers=user.headers)
    assert csv_res.status_code == 200
    assert csv_res.content.startswith("﻿".encode()) and "attachment" in csv_res.headers["content-disposition"]
    assert csv_res.headers["x-export-count"] == "2"
    rows = csv_res.content.decode("utf-8-sig").splitlines()
    assert rows[0].startswith("Chữ Hán,Pinyin,Nghĩa,Cấp HSK,Trạng thái,Ghi chú") and len(rows) == 3
    assert any(
        "朋友" in r and "Đã thuộc" in r and "'=HYPERLINK(1)" in r for r in rows
    )  # chống chèn công thức

    filtered = await client.get(f"{VOCAB}/export?format=csv&status=known", headers=user.headers)
    assert filtered.headers["x-export-count"] == "1"
    anki = await client.get(f"{VOCAB}/export?format=anki", headers=user.headers)
    lines = anki.content.decode("utf-8").splitlines()
    assert lines[0] == "#separator:tab" and lines[3].split("\t")[0] in {"你好", "朋友"}
    assert len(lines[3].split("\t")) == 3 and lines[3].split("\t")[2].startswith("YingHua")
    assert (await client.get(f"{VOCAB}/export?format=pdf", headers=user.headers)).status_code == 400
    assert (
        await client.get(f"{VOCAB}/export?format=csv", headers=other.headers)
    ).status_code == 404  # chỉ của mình

    admin = await make_admin(app, client)
    as_admin = await client.get(
        f"{API}/admin/users/{user.id}/vocab-entries/export?format=csv", headers=admin.headers
    )
    assert as_admin.status_code == 200 and as_admin.headers["x-export-count"] == "2"


async def test_backfill_is_idempotent(app: FastAPI, client: httpx.AsyncClient) -> None:
    """Script nạp bù tính lại từ bảng nguồn và ghi đè nên chạy lại không nhân đôi số liệu."""
    from app.modules.stats.infrastructure.backfill import SqlActivityBackfill

    user = await register(client)
    await _save_and_grade(client, app, user)
    before = (await client.get(f"{API}/stats/activity?count=3", headers=user.headers)).json()["points"]
    factory = app.state.container.session_factory
    for _ in range(2):
        async with factory() as session:
            await SqlActivityBackfill(session).run()
            await session.commit()
    after = (await client.get(f"{API}/stats/activity?count=3", headers=user.headers)).json()["points"]
    assert before == after
