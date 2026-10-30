"""M04 Xử lý ảnh + M05 Đọc truyện — luồng chính, phân quyền, hàng đợi (F04.02–F04.07, F05.01–F05.08)."""

from __future__ import annotations

import asyncio
import random
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.stored_files import FileKind
from app.modules.imaging.application.dto import ClaimedJob, JobResult
from app.modules.imaging.application.worker import WorkerJobs
from app.modules.imaging.domain.entities import NewBubble
from app.modules.imaging.domain.errors import InvalidBubbleError, JobNotRunningError
from app.modules.imaging.infrastructure.worker import build_worker_jobs
from tests.helpers import Account, error_code, make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _color() -> tuple[int, int, int]:
    """Màu ngẫu nhiên: ảnh khác nội dung thì không bị dùng lại bản dịch `done` của lần chạy trước (F04.14)."""
    return random.randrange(256), random.randrange(256), random.randrange(256)


def _worker(app: FastAPI) -> WorkerJobs:
    c = app.state.container
    return build_worker_jobs(c.session_factory, c.storage, c.clock, c.settings)


def _bubbles() -> list[NewBubble]:
    return [
        NewBubble(
            idx=0,
            class_name="speech_bubble",
            x=6,
            y=9,
            w=12,
            h=18,
            text_zh="你好吗",
            polygon=[[6, 9], [18, 9], [18, 27], [6, 27]],
            confidence=0.93,
            pinyin="nǐ hǎo ma",
            text_vi="Bạn khỏe không",
            translate_method="vietphrase",
            lines=["你好吗"],
            tokens=[
                {"word": "你好", "pinyin": "nǐ hǎo", "entry_id": None},
                {"word": "吗", "pinyin": "ma", "entry_id": None},
            ],
            style={"color": "#000000"},
        ),
        NewBubble(idx=1, class_name="sound_effect", x=0, y=0, w=4, h=4, text_zh="咚"),
    ]


async def _drain(jobs: WorkerJobs) -> None:
    """Đóng mọi việc tồn từ các lần chạy test trước để việc của test hiện tại là việc duy nhất.

    Đóng bằng `failed` (không phải `done`) để không tạo bản dịch `done` rỗng bị ảnh trùng dùng lại (F04.14).
    """
    while (job := await jobs.claim_next_job("drain", _now())) is not None:
        await jobs.fail_job(job.translation_id, "test", "Dọn hàng đợi của test")


async def _claim_mine(jobs: WorkerJobs, translation_id: int) -> ClaimedJob:
    while (job := await jobs.claim_next_job("w1", _now())) is not None:
        if job.translation_id == translation_id:
            return job
        await jobs.fail_job(job.translation_id, "test", "Dọn hàng đợi của test")
    raise AssertionError("Việc của test không có trong hàng đợi")


async def _complete(jobs: WorkerJobs, translation_id: int) -> None:
    await _claim_mine(jobs, translation_id)
    inpainted = await jobs.store_result_image(png_bytes((1, 2, 3)), FileKind.INPAINTED)
    rendered = await jobs.store_result_image(png_bytes((4, 5, 6)), FileKind.RENDERED)
    await jobs.complete_job(
        translation_id,
        JobResult(_bubbles(), inpainted, rendered, stats={"bubbles": 2}, processing_ms=1200),
    )


async def _new_page(
    client: httpx.AsyncClient, who: Account, series_id: int | None = None, chapter_id: int | None = None
) -> dict[str, Any]:
    """Tạo (nếu cần) truyện + chương rồi tải một trang; trả JSON trang kèm series_id/chapter_id."""
    if series_id is None:
        res = await client.post(f"{API}/series", json={"title_vi": "Hoa Hồng"}, headers=who.headers)
        series_id = res.json()["id"]
    if chapter_id is None:
        res = await client.post(f"{API}/series/{series_id}/chapters", json={"number": 1}, headers=who.headers)
        chapter_id = res.json()["id"]
    up = await client.post(
        f"{API}/chapters/{chapter_id}/pages",
        files=[("files", ("p.png", png_bytes(_color()), "application/octet-stream"))],
        headers=who.headers,
    )
    assert up.status_code == 201, up.text
    page: dict[str, Any] = up.json()["results"][0]["page"]
    page["chapter_id"], page["series_id"] = chapter_id, series_id
    return page


async def _translation_id(client: httpx.AsyncClient, who: Account, page_id: int) -> int:
    res = await client.get(f"{API}/pages/{page_id}/status", headers=who.headers)
    assert res.status_code == 200, res.text
    return int(res.json()["translation_id"])


async def test_page_status_retranslate_download_reading_and_personal_data(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-18..21, 24, 25, 63, 64: trạng thái, dịch lại, tải ảnh, đọc, sửa dịch, dấu trang, ghi chú."""
    owner, other = await register(client), await register(client)
    jobs = _worker(app)
    await _drain(jobs)
    page = await _new_page(client, owner)
    pid = page["id"]
    tid = await _translation_id(client, owner, pid)

    # F04.02: trạng thái; người khác không xem được.
    status = (await client.get(f"{API}/pages/{pid}/status", headers=owner.headers)).json()
    assert (status["status"], status["attempts"], status["can_retranslate"]) == ("queued", 0, False)
    assert (await client.get(f"{API}/pages/{pid}/status", headers=other.headers)).status_code == 404
    assert (await client.get(f"{API}/pages/{pid}/status")).status_code == 404

    # F04.03: trang đang chờ thì từ chối; người khác 404; chưa đăng nhập 401.
    busy = await client.post(f"{API}/pages/{pid}/retranslate", headers=owner.headers)
    assert (busy.status_code, error_code(busy)) == (409, "TRANSLATION_IN_PROGRESS")
    assert (await client.post(f"{API}/pages/{pid}/retranslate", headers=other.headers)).status_code == 404
    assert (await client.post(f"{API}/pages/{pid}/retranslate")).status_code == 401

    # F04.13: lỗi lần 1 → xếp hàng lại; lỗi lần 2 → failed kèm lý do ≤ 1000 ký tự.
    await _claim_mine(jobs, tid)
    assert (await jobs.fail_job(tid, "ocr", "lỗi " * 600)).value == "queued"
    await _claim_mine(jobs, tid)
    assert (await jobs.fail_job(tid, "ocr", "lỗi " * 600)).value == "failed"
    failed = (await client.get(f"{API}/pages/{pid}/status", headers=owner.headers)).json()
    assert (failed["status"], failed["error_step"], failed["can_retranslate"]) == ("failed", "ocr", True)
    assert failed["attempts"] == 2 and len(failed["error_message"]) <= 1000
    download_failed = await client.get(f"{API}/pages/{pid}/download?variant=rendered", headers=owner.headers)
    assert (download_failed.status_code, error_code(download_failed)) == (409, "IMAGE_NOT_READY")

    # F04.03: dịch lại → queued, số lần thử về 0, lý do lỗi xóa.
    again = await client.post(f"{API}/pages/{pid}/retranslate", headers=owner.headers)
    assert again.status_code == 202 and again.json() == {
        "page_id": pid,
        "translation_id": tid,
        "status": "queued",
    }
    requeued = (await client.get(f"{API}/pages/{pid}/status", headers=owner.headers)).json()
    assert (requeued["status"], requeued["attempts"], requeued["error_message"]) == ("queued", 0, None)

    # Worker hoàn tất: bong bóng sai loại bị từ chối, đúng thì ghi và đặt done.
    await _claim_mine(jobs, tid)
    with pytest.raises(InvalidBubbleError):
        await jobs.complete_job(tid, JobResult([NewBubble(0, "bogus", 0, 0, 1, 1, "字")]))
    inpainted = await jobs.store_result_image(png_bytes((1, 2, 3)), FileKind.INPAINTED)
    rendered = await jobs.store_result_image(png_bytes((4, 5, 6)), FileKind.RENDERED)
    await jobs.complete_job(tid, JobResult(_bubbles(), inpainted, rendered, {"bubbles": 2}, 900))
    with pytest.raises(JobNotRunningError):
        await jobs.complete_job(tid, JobResult(_bubbles(), inpainted, rendered))
    done = (await client.get(f"{API}/pages/{pid}/status", headers=owner.headers)).json()
    assert (done["status"], done["can_retranslate"]) == ("done", False)
    not_failed = await client.post(f"{API}/pages/{pid}/retranslate", headers=owner.headers)
    assert (not_failed.status_code, error_code(not_failed)) == (409, "TRANSLATION_NOT_FAILED")

    # F04.04: tải đúng dạng, có Content-Disposition; người khác 404; dạng sai tham số 422.
    for variant in ("original", "inpainted", "rendered"):
        res = await client.get(f"{API}/pages/{pid}/download?variant={variant}", headers=owner.headers)
        assert res.status_code == 200 and res.headers["content-type"] == "image/png"
        assert f"{variant}.png" in res.headers["content-disposition"]
        assert res.headers["content-disposition"].startswith("attachment;")
    assert (await client.get(f"{API}/pages/{pid}/download", headers=other.headers)).status_code == 404
    assert (
        await client.get(f"{API}/pages/{pid}/download?variant=zip", headers=owner.headers)
    ).status_code == 422

    # F05.01: dữ liệu đọc trang — ba dạng ảnh, bong bóng pixel + phần trăm, token.
    reading = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()
    assert reading["page"]["status"] == "done" and reading["annotation"] is None
    assert all(
        reading["variants"][k].startswith("/api/v1/files/") for k in ("original", "inpainted", "rendered")
    )
    first, second = reading["bubbles"]
    assert (first["x_pct"], first["y_pct"], first["w_pct"], first["h_pct"]) == (25.0, 25.0, 50.0, 50.0)
    assert (first["text_vi"], first["text_vi_effective"], first["has_edit"]) == ("Bạn khỏe không",) * 2 + (
        False,
    )
    assert first["tokens"][0] == {"word": "你好", "pinyin": "nǐ hǎo", "entry_id": None}
    assert second["class_name"] == "sound_effect" and second["text_vi"] is None
    assert (await client.get(f"{API}/pages/{pid}/reading", headers=other.headers)).status_code == 404
    assert (await client.get(f"{API}/pages/{pid}/reading")).status_code == 404
    bid = first["id"]

    # F05.05, F05.06: bản sửa dịch riêng; người khác không thấy và không sửa được; hoàn tác lặp không lỗi.
    edit_url = f"{API}/bubbles/{bid}/edit"
    assert (await client.put(edit_url, json={"text_vi": "x"}, headers=other.headers)).status_code == 404
    assert (await client.put(edit_url, json={"text_vi": "x"})).status_code == 401
    assert (await client.put(edit_url, json={"text_vi": ""}, headers=owner.headers)).status_code == 422
    assert (
        await client.put(edit_url, json={"text_vi": "a" * 1001}, headers=owner.headers)
    ).status_code == 422
    blank = await client.put(edit_url, json={"text_vi": "   "}, headers=owner.headers)
    assert (blank.status_code, error_code(blank)) == (400, "EMPTY_TRANSLATION")
    saved = await client.put(edit_url, json={"text_vi": "  Chào bạn  "}, headers=owner.headers)
    assert saved.json() == {
        "bubble_id": bid,
        "text_vi": "Bạn khỏe không",
        "text_vi_effective": "Chào bạn",
        "has_edit": True,
    }
    mine = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()["bubbles"][0]
    assert (mine["text_vi_effective"], mine["has_edit"]) == ("Chào bạn", True)
    assert (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()["bubbles"][0][
        "text_vi"
    ] == ("Bạn khỏe không")
    assert (await client.delete(edit_url, headers=other.headers)).status_code == 404
    assert (await client.delete(edit_url, headers=owner.headers)).status_code == 204
    assert (await client.delete(edit_url, headers=owner.headers)).status_code == 204
    back = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()["bubbles"][0]
    assert (back["text_vi_effective"], back["has_edit"]) == ("Bạn khỏe không", False)

    # F05.02: người đã đăng nhập tra từ trong bong bóng (không hạn mức); từ ngoài bong bóng bị từ chối.
    hover = await client.get(f"{API}/bubbles/{bid}/lookup", params={"word": "你好"}, headers=owner.headers)
    assert hover.status_code == 200 and hover.json()["guest"] is None
    assert hover.json()["lookup"]["limited"] is False and hover.json()["lookup"]["term"] == "你好"
    outside = await client.get(f"{API}/bubbles/{bid}/lookup", params={"word": "再见"}, headers=owner.headers)
    assert (outside.status_code, error_code(outside)) == (400, "WORD_NOT_IN_BUBBLE")
    hidden = await client.get(f"{API}/bubbles/{bid}/lookup", params={"word": "你好"}, headers=other.headers)
    assert (hidden.status_code, error_code(hidden)) == (404, "BUBBLE_NOT_FOUND")

    # F05.07: dấu trang và danh sách trang đã lưu, lọc theo người dùng.
    assert (await client.put(f"{API}/pages/{pid}/bookmark", json={"is_bookmarked": True})).status_code == 401
    assert (
        await client.put(f"{API}/pages/{pid}/bookmark", json={"is_bookmarked": True}, headers=other.headers)
    ).status_code == 404
    marked = await client.put(
        f"{API}/pages/{pid}/bookmark", json={"is_bookmarked": True}, headers=owner.headers
    )
    assert marked.json() == {"page_id": pid, "is_bookmarked": True}
    saved_pages = (await client.get(f"{API}/bookmarks", headers=owner.headers)).json()
    assert saved_pages["total"] == 1 and (saved_pages["page"], saved_pages["size"]) == (1, 20)
    item = saved_pages["items"][0]
    assert (item["page_id"], item["page_no"], item["series_title"], item["chapter_number"]) == (
        pid,
        1,
        "Hoa Hồng",
        1.0,
    )
    assert (await client.get(f"{API}/bookmarks", headers=other.headers)).json()["total"] == 0
    assert (await client.get(f"{API}/bookmarks")).status_code == 401

    # F05.08: ghi chú — kiểm hợp lệ, lưu, đọc lại, xóa nhưng giữ dấu trang.
    notes_url = f"{API}/pages/{pid}/annotations"
    stroke = {"color": "#112233", "points": [{"x": 1.5, "y": 2}, {"x": 3, "y": 4.25}]}
    body = {"highlights": {str(bid): "#ff00aa"}, "strokes": [stroke]}
    assert (await client.put(notes_url, json=body, headers=other.headers)).status_code == 404
    assert (await client.put(notes_url, json=body)).status_code == 401
    bad_color = await client.put(notes_url, json={"highlights": {str(bid): "pink"}}, headers=owner.headers)
    assert (bad_color.status_code, error_code(bad_color)) == (400, "INVALID_ANNOTATION")
    bad_key = await client.put(notes_url, json={"highlights": {"abc": "#ff00aa"}}, headers=owner.headers)
    assert bad_key.status_code == 422
    too_many = {"strokes": [{"color": "#000000", "points": [{"x": 0, "y": 0}]}] * 501}
    big = await client.put(notes_url, json=too_many, headers=owner.headers)
    assert (big.status_code, error_code(big)) == (413, "ANNOTATION_TOO_LARGE")
    ok = await client.put(notes_url, json=body, headers=owner.headers)
    assert ok.status_code == 200 and ok.json()["is_bookmarked"] is True  # giữ dấu trang
    assert ok.json()["highlights"] == {str(bid): "#ff00aa"} and ok.json()["strokes"] == [stroke]
    annotation = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()["annotation"]
    assert annotation["strokes"] == [stroke] and annotation["highlights"] == {str(bid): "#ff00aa"}
    assert (await client.delete(notes_url, headers=other.headers)).status_code == 404
    assert (await client.delete(notes_url, headers=owner.headers)).status_code == 204
    after = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()["annotation"]
    assert (after["highlights"], after["strokes"], after["is_bookmarked"]) == ({}, [], True)
    # Bỏ dấu trang rồi xóa ghi chú → không còn dòng nào.
    await client.put(f"{API}/pages/{pid}/bookmark", json={"is_bookmarked": False}, headers=owner.headers)
    assert (await client.get(f"{API}/bookmarks", headers=owner.headers)).json()["total"] == 0
    assert (await client.delete(notes_url, headers=owner.headers)).status_code == 204
    assert (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()[
        "annotation"
    ] is None


async def test_guest_trial_reading_lookup_limit_admin_queue_and_claim_contention(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-KH-04/05, US-QT-06/07, US-XL-01: Khách đọc thử + hạn mức, giám sát hàng đợi, tranh việc."""
    admin, learner = await make_admin(app, client), await register(client)
    jobs = _worker(app)
    await _drain(jobs)
    app.state.container.settings.guest_lookup_limit = 2

    series = (
        await client.post(
            f"{API}/series", json={"title_vi": "Công khai", "visibility": "public"}, headers=admin.headers
        )
    ).json()["id"]
    trial_ch = (
        await client.post(
            f"{API}/series/{series}/chapters", json={"number": 1, "is_trial": True}, headers=admin.headers
        )
    ).json()["id"]
    locked_ch = (
        await client.post(f"{API}/series/{series}/chapters", json={"number": 2}, headers=admin.headers)
    ).json()["id"]
    trial_page = await _new_page(client, admin, series, trial_ch)
    locked_page = await _new_page(client, admin, series, locked_ch)
    trial_tid = await _translation_id(client, admin, trial_page["id"])
    await _complete(jobs, trial_tid)
    await _complete(jobs, await _translation_id(client, admin, locked_page["id"]))

    # F05.01 + F03.03: Khách đọc được chương đọc thử, không có ghi chú; chương khoá → yêu cầu đăng nhập.
    guest_reading = await client.get(f"{API}/pages/{trial_page['id']}/reading")
    assert guest_reading.status_code == 200 and guest_reading.json()["annotation"] is None
    bubble_id = guest_reading.json()["bubbles"][0]["id"]
    locked = await client.get(f"{API}/pages/{locked_page['id']}/reading")
    assert (locked.status_code, error_code(locked)) == (401, "LOGIN_REQUIRED")
    locked_bubble = (
        await client.get(f"{API}/pages/{locked_page['id']}/reading", headers=learner.headers)
    ).json()["bubbles"][0]["id"]
    assert (
        await client.get(f"{API}/bubbles/{locked_bubble}/lookup", params={"word": "你好"})
    ).status_code == 404
    assert (await client.put(f"{API}/bubbles/{bubble_id}/edit", json={"text_vi": "x"})).status_code == 401

    # F05.04: hạn mức theo phiên; hết lượt → 429, không trả kết quả; phiên khác độc lập.
    lookup_url = f"{API}/bubbles/{bubble_id}/lookup"
    first = await client.get(lookup_url, params={"word": "你好"})
    assert first.status_code == 200, first.text
    guest = first.json()["guest"]
    assert (guest["used"], guest["remaining"], guest["limit"]) == (1, 1, 2)
    assert first.json()["lookup"]["limited"] is True
    assert first.headers["x-guest-session"] == guest["session_id"]
    session = {"X-Guest-Session": guest["session_id"]}
    second = await client.get(lookup_url, params={"word": "你好"}, headers=session)
    assert second.json()["guest"]["remaining"] == 0
    blocked = await client.get(lookup_url, params={"word": "你好"}, headers=session)
    assert (blocked.status_code, error_code(blocked)) == (429, "GUEST_LOOKUP_LIMIT_REACHED")
    assert blocked.json()["error"]["details"]["login_required"] is True
    fresh = await client.get(lookup_url, params={"word": "你好"}, headers={"X-Guest-Session": "not-a-uuid"})
    assert fresh.status_code == 200 and fresh.json()["guest"]["used"] == 1
    assert fresh.json()["guest"]["session_id"] != guest["session_id"]
    member = await client.get(lookup_url, params={"word": "你好"}, headers=learner.headers)
    assert member.status_code == 200 and member.json()["guest"] is None  # người đã đăng nhập: không hạn mức

    # F04.03: người đọc được nhưng không có quyền sửa trang công khai → 403; F04.05/F04.06: chỉ admin.
    forbidden = await client.post(f"{API}/pages/{trial_page['id']}/retranslate", headers=learner.headers)
    assert (forbidden.status_code, error_code(forbidden)) == (403, "PERMISSION_DENIED")
    assert (await client.get(f"{API}/admin/translations", headers=learner.headers)).status_code == 403
    assert (await client.get(f"{API}/admin/translations")).status_code == 401
    assert (
        await client.post(f"{API}/admin/translations/1/retry", headers=learner.headers)
    ).status_code == 403

    # Trang mới → lỗi hai lần → admin thấy ở bộ lọc `failed`, chạy lại được đúng một lần.
    third = await _new_page(client, admin, series, trial_ch)
    tid = await _translation_id(client, admin, third["id"])
    await _claim_mine(jobs, tid)
    await jobs.fail_job(tid, "inpaint", "mất bộ nhớ")
    await _claim_mine(jobs, tid)
    await jobs.fail_job(tid, "inpaint", "mất bộ nhớ")
    listing = (
        await client.get(f"{API}/admin/translations?status=failed&size=100", headers=admin.headers)
    ).json()
    row = next(i for i in listing["items"] if i["id"] == tid)
    assert (row["status"], row["error_step"], row["error_message"], row["attempts"]) == (
        "failed",
        "inpaint",
        "mất bộ nhớ",
        2,
    )
    assert (
        set(listing["counts"]) == {"queued", "running", "done", "failed"} and listing["counts"]["failed"] >= 1
    )
    assert listing["avg_processing_ms"] is None or listing["avg_processing_ms"] >= 0
    assert (
        await client.get(f"{API}/admin/translations?status=bogus", headers=admin.headers)
    ).status_code == 422
    retry = await client.post(f"{API}/admin/translations/{tid}/retry", headers=admin.headers)
    assert retry.status_code == 202 and retry.json()["status"] == "queued"
    busy = await client.post(f"{API}/admin/translations/{tid}/retry", headers=admin.headers)
    assert (busy.status_code, error_code(busy)) == (409, "TRANSLATION_IN_PROGRESS")
    missing = await client.post(f"{API}/admin/translations/999999999/retry", headers=admin.headers)
    assert (missing.status_code, error_code(missing)) == (404, "TRANSLATION_NOT_FOUND")

    # F04.07: hai worker tranh một việc → đúng một worker nhận được (SKIP LOCKED + giao dịch riêng).
    await _drain(jobs)
    await _new_page(client, admin, series, trial_ch)
    claims = await asyncio.gather(jobs.claim_next_job("w-a", _now()), jobs.claim_next_job("w-b", _now()))
    assert sorted(c is not None for c in claims) == [False, True]


async def test_text_ready_and_reading_return_bubbles_while_images_still_running(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """F04.02, F05.01: sau giai đoạn chữ (còn running) trang đọc được, id bong bóng giữ nguyên."""
    owner = await register(client)
    jobs = _worker(app)
    await _drain(jobs)
    page = await _new_page(client, owner)
    pid = page["id"]
    tid = await _translation_id(client, owner, pid)

    queued = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()
    assert (queued["page"]["status"], queued["page"]["text_ready"], queued["bubbles"]) == (
        "queued",
        False,
        [],
    )
    assert (await client.get(f"{API}/pages/{pid}", headers=owner.headers)).json()["text_ready"] is False

    await _claim_mine(jobs, tid)
    await jobs.save_text_result(tid, [replace(b, style=None) for b in _bubbles()], {"mode": "yolo"})
    running = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()
    assert (running["page"]["status"], running["page"]["text_ready"]) == ("running", True)
    assert running["variants"]["inpainted"] is None and running["variants"]["rendered"] is None
    ids = [b["id"] for b in running["bubbles"]]
    assert len(ids) == 2 and running["bubbles"][0]["style"] is None
    status = (await client.get(f"{API}/pages/{pid}/status", headers=owner.headers)).json()
    assert (status["status"], status["text_ready"]) == ("running", True)
    assert (await client.get(f"{API}/pages/{pid}", headers=owner.headers)).json()["text_ready"] is True
    download = await client.get(f"{API}/pages/{pid}/download?variant=rendered", headers=owner.headers)
    assert download.status_code == 409  # ảnh chưa xong vẫn bị chặn

    inpainted = await jobs.store_result_image(png_bytes((1, 2, 3)), FileKind.INPAINTED)
    rendered = await jobs.store_result_image(png_bytes((4, 5, 6)), FileKind.RENDERED)
    await jobs.complete_job(tid, JobResult(_bubbles(), inpainted, rendered, {"bubbles": 2}, 900))
    done = (await client.get(f"{API}/pages/{pid}/reading", headers=owner.headers)).json()
    assert done["page"]["text_ready"] is True and [b["id"] for b in done["bubbles"]] == ids
    assert done["bubbles"][0]["style"] == {"color": "#000000"}
    assert done["variants"]["rendered"] is not None


async def test_upload_more_than_twenty_files_is_rejected(app: FastAPI, client: httpx.AsyncClient) -> None:
    """F03.07: tối đa 20 ảnh mỗi lần."""
    owner = await register(client)
    series = (await client.post(f"{API}/series", json={"title_vi": "Nhiều"}, headers=owner.headers)).json()
    chapter = (
        await client.post(f"{API}/series/{series['id']}/chapters", json={"number": 1}, headers=owner.headers)
    ).json()
    files = [("files", (f"p{i}.png", png_bytes(_color()), "image/png")) for i in range(21)]
    res = await client.post(f"{API}/chapters/{chapter['id']}/pages", files=files, headers=owner.headers)
    assert (res.status_code, error_code(res)) == (400, "TOO_MANY_FILES")
    assert "tối đa 20 ảnh" in res.json()["error"]["message"]
