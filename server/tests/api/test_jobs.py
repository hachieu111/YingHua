"""M15 Tác vụ nền — dọn ảnh tải nhanh hết hạn, phiên, tệp mồ côi; lập lịch và khóa (F15.01–F15.03)."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from app.core.stored_files import FileKind
from app.modules.imaging.infrastructure.worker import build_worker_jobs
from app.modules.jobs.infrastructure.tasks import build_job_runner
from tests.conftest import FixedClock
from tests.helpers import make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"
JOB_NAMES = ["cleanup_orphan_files", "cleanup_quick_uploads", "cleanup_sessions"]


def _png() -> bytes:
    return png_bytes((random.randrange(256), random.randrange(256), random.randrange(256)))


async def _scalar(app: FastAPI, sql: str, **params: object) -> object:
    async with app.state.container.session_factory() as session:
        return (await session.execute(text(sql), params)).scalar_one()


async def _execute(app: FastAPI, sql: str, **params: object) -> None:
    async with app.state.container.session_factory() as session:
        await session.execute(text(sql), params)
        await session.commit()


async def test_run_due_jobs_cleans_expired_data_keeps_series_pages_and_records_runs(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-HG-01 TC1–TC6: dọn ảnh tải nhanh hết hạn, phiên Khách, tệp mồ côi; lập lịch, khóa, nhật ký chạy."""
    owner, admin = await register(client), await make_admin(app, client)
    container = app.state.container

    # Dữ liệu: ảnh tải nhanh (sẽ hết hạn), trang của truyện (không bao giờ bị dọn), tệp kết quả mồ côi.
    quick = await client.post(
        f"{API}/quick-uploads",
        files={"file": ("a.png", _png(), "application/octet-stream")},
        headers=owner.headers,
    )
    assert quick.status_code == 201, quick.text
    series = (await client.post(f"{API}/series", json={"title_vi": "Giữ lại"}, headers=owner.headers)).json()[
        "id"
    ]
    chapter = (
        await client.post(f"{API}/series/{series}/chapters", json={"number": 1}, headers=owner.headers)
    ).json()["id"]
    kept = (
        await client.post(
            f"{API}/chapters/{chapter}/pages",
            files=[("files", ("b.png", _png(), "application/octet-stream"))],
            headers=owner.headers,
        )
    ).json()["results"][0]["page"]
    worker = build_worker_jobs(
        container.session_factory, container.storage, container.clock, container.settings
    )
    orphan_id = await worker.store_result_image(_png(), FileKind.RENDERED)
    guest_id = uuid.uuid4()
    await _execute(
        app,
        "INSERT INTO guest_sessions (id, lookup_count, created_at, expires_at) "
        "VALUES (:id, 1, now() - interval '3 days', now() - interval '2 days')",
        id=guest_id,
    )
    await _execute(
        app, "UPDATE scheduled_jobs SET last_started_at = NULL, locked_until = NULL, locked_by = NULL"
    )

    # 8 ngày sau: ảnh tải nhanh (hạn 7 ngày) và tệp mồ côi đều quá hạn.
    later = datetime.now(timezone.utc) + timedelta(days=8)
    runner = build_job_runner(container.session_factory, container.storage, FixedClock(later), 60)
    reports = await runner.run_due_jobs(later, "w1")
    assert [r.name for r in reports] == JOB_NAMES
    assert all(r.status.value == "ok" and r.error_message is None for r in reports), reports
    by_name = {r.name: r.summary for r in reports}
    assert by_name["cleanup_quick_uploads"] is not None and by_name["cleanup_quick_uploads"]["pages"] >= 1
    assert by_name["cleanup_sessions"] is not None and by_name["cleanup_sessions"]["guest_sessions"] >= 1
    assert by_name["cleanup_orphan_files"] is not None and by_name["cleanup_orphan_files"]["files"] >= 1

    # F15.01: ảnh tải nhanh biến mất (cả tệp gốc); trang trong truyện còn nguyên.
    quick_page = quick.json()
    assert (await client.get(f"{API}/pages/{quick_page['id']}", headers=owner.headers)).status_code == 404
    assert (await client.get(quick_page["original_url"], headers=owner.headers)).status_code == 404
    assert (await client.get(f"{API}/pages/{kept['id']}", headers=owner.headers)).status_code == 200
    assert (await client.get(kept["original_url"], headers=owner.headers)).status_code == 200
    # F15.02 + F15.03: phiên Khách hết hạn và tệp mồ côi đã bị xóa.
    assert await _scalar(app, "SELECT count(*) FROM guest_sessions WHERE id = :id", id=guest_id) == 0
    assert await _scalar(app, "SELECT count(*) FROM stored_files WHERE id = :id", id=orphan_id) == 0

    # F15.03: chạy lại ngay thì chưa đến hạn; sau 2 giờ chỉ tác vụ chu kỳ 60 phút chạy lại; khóa đã nhả.
    assert await runner.run_due_jobs(later, "w1") == []
    runner_2h = build_job_runner(
        container.session_factory, container.storage, FixedClock(later + timedelta(hours=2)), 60
    )
    again = await runner_2h.run_due_jobs(later + timedelta(hours=2), "w2")
    assert [r.name for r in again] == ["cleanup_quick_uploads"]
    assert await _scalar(app, "SELECT count(*) FROM scheduled_jobs WHERE locked_by IS NOT NULL") == 0
    assert await _scalar(app, "SELECT count(*) FROM job_runs WHERE status = 'running'") == 0

    # Khóa chống chạy chồng: tác vụ đang bị khóa chưa hết hạn thì worker khác không nhận.
    await _execute(
        app,
        "UPDATE scheduled_jobs SET last_started_at = NULL, locked_by = 'other', locked_until = :until "
        "WHERE name = 'cleanup_sessions'",
        until=later + timedelta(hours=3),
    )
    locked = await runner_2h.run_due_jobs(later + timedelta(hours=2), "w3")
    assert "cleanup_sessions" not in [r.name for r in locked]

    # Admin xem trạng thái tác vụ và lần chạy gần nhất; người học/Khách bị từ chối.
    listing = await client.get(f"{API}/admin/jobs", headers=admin.headers)
    assert listing.status_code == 200, listing.text
    items = {i["name"]: i for i in listing.json()["items"]}
    assert sorted(items) == JOB_NAMES
    quick_job = items["cleanup_quick_uploads"]
    assert quick_job["interval_seconds"] == 3600 and quick_job["last_status"] == "ok"
    assert quick_job["last_run"]["status"] == "ok" and "pages" in quick_job["last_run"]["summary"]
    assert quick_job["next_run_at"] is not None
    assert (await client.get(f"{API}/admin/jobs", headers=owner.headers)).status_code == 403
    assert (await client.get(f"{API}/admin/jobs")).status_code == 401
