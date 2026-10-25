"""M03 Thư viện — luồng chính, phân quyền, tiến độ, Thư viện cá nhân, chấm sao (F03.02–F03.14)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.helpers import Account, error_code, make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"


def _files(*images: tuple[str, bytes]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (name, data, "application/octet-stream")) for name, data in images]


async def _new_series(client: httpx.AsyncClient, who: Account, title: str, **extra: Any) -> dict[str, Any]:
    res = await client.post(f"{API}/series", json={"title_vi": title, **extra}, headers=who.headers)
    assert res.status_code == 201, res.text
    data: dict[str, Any] = res.json()
    return data


async def test_private_series_chapters_pages_and_ownership(client: httpx.AsyncClient) -> None:
    """US-NH-10, 11, 12, 14, 15: tạo, thêm chương, tải trang, quyền sở hữu."""
    owner, other = await register(client), await register(client)

    series = await _new_series(client, owner, "Hoa Hồng", genres=["Tình cảm"], est_hsk_level=3)
    sid = series["id"]
    assert (series["visibility"], series["can_edit"], series["genres"]) == ("private", True, ["Tình cảm"])

    # Trùng tên: cảnh báo, chỉ tạo khi xác nhận (F03.04).
    dup = await client.post(f"{API}/series", json={"title_vi": "hoa hồng"}, headers=owner.headers)
    assert (dup.status_code, error_code(dup)) == (409, "SERIES_TITLE_DUPLICATE")
    await _new_series(client, owner, "hoa hồng", confirm_duplicate=True)

    # Người học không được đăng công khai (F03.05).
    res = await client.post(
        f"{API}/series", json={"title_vi": "Z", "visibility": "public"}, headers=owner.headers
    )
    assert (res.status_code, error_code(res)) == (403, "PUBLISH_REQUIRES_ADMIN")

    # Người khác và Khách: 404 như không tồn tại (F03.10).
    assert (await client.get(f"{API}/series/{sid}", headers=other.headers)).status_code == 404
    assert (await client.get(f"{API}/series/{sid}")).status_code == 404
    assert (
        await client.patch(f"{API}/series/{sid}", json={"title_vi": "x"}, headers=other.headers)
    ).status_code == 404
    assert (await client.delete(f"{API}/series/{sid}", headers=other.headers)).status_code == 404
    assert (await client.post(f"{API}/series", json={"title_vi": "x"})).status_code == 401

    mine = (await client.get(f"{API}/series?scope=mine", headers=owner.headers)).json()
    assert mine["total"] == 2
    public = (await client.get(f"{API}/series", headers=owner.headers)).json()
    assert all(i["id"] != sid for i in public["items"])
    assert (await client.get(f"{API}/series?scope=mine")).status_code == 401
    found = (
        await client.get(f"{API}/series?scope=mine&q=HOA&hsk=3&genre=Tình cảm", headers=owner.headers)
    ).json()
    assert [i["id"] for i in found["items"]] == [sid]

    # Chương: số trùng → 409; cờ đọc thử chỉ admin (F03.06, F03.05).
    ch = await client.post(
        f"{API}/series/{sid}/chapters", json={"number": 1, "title": "Mở đầu"}, headers=owner.headers
    )
    assert ch.status_code == 201 and ch.json()["number"] == 1.0
    cid = ch.json()["id"]
    dup_ch = await client.post(f"{API}/series/{sid}/chapters", json={"number": "1.0"}, headers=owner.headers)
    assert (dup_ch.status_code, error_code(dup_ch)) == (409, "CHAPTER_NUMBER_TAKEN")
    trial = await client.post(
        f"{API}/series/{sid}/chapters", json={"number": 2, "is_trial": True}, headers=owner.headers
    )
    assert (trial.status_code, error_code(trial)) == (403, "PUBLISH_REQUIRES_ADMIN")
    assert (
        await client.post(f"{API}/series/{sid}/chapters", json={"number": 3}, headers=other.headers)
    ).status_code == 404

    # Tải trang: ảnh hợp lệ, ảnh trùng, tệp sai định dạng, tệp rỗng — kết quả riêng từng tệp (F03.07).
    img1, img2 = png_bytes((10, 20, 30)), png_bytes((90, 80, 70))
    up = await client.post(
        f"{API}/chapters/{cid}/pages",
        files=_files(
            ("a.png", img1), ("b.png", img2), ("a-copy.png", img1), ("note.txt", b"hi"), ("bad.png", b"not")
        ),
        headers=owner.headers,
    )
    assert up.status_code == 201, up.text
    results = up.json()["results"]
    assert up.json()["created"] == 2
    assert [r["error"]["code"] if r["error"] else None for r in results] == [
        None,
        None,
        "PAGE_ALREADY_EXISTS",
        "UNSUPPORTED_IMAGE_TYPE",
        "UNSUPPORTED_IMAGE_TYPE",
    ]
    pages = [r["page"] for r in results if r["page"]]
    assert [p["page_no"] for p in pages] == [1, 2]
    assert pages[0]["status"] == "queued" and pages[0]["rendered_url"] is None

    detail = (await client.get(f"{API}/chapters/{cid}", headers=owner.headers)).json()
    assert [p["id"] for p in detail["pages"]] == [p["id"] for p in pages] and detail["can_edit"] is True
    assert (await client.get(f"{API}/chapters/{cid}", headers=other.headers)).status_code == 404

    # Tệp ảnh: chủ xem được, người khác/Khách không (F03.10), không lộ đường dẫn.
    url = pages[0]["original_url"]
    assert url.startswith("/api/v1/files/")
    served = await client.get(url, headers=owner.headers)
    assert (served.status_code, served.headers["content-type"]) == (200, "image/png")
    assert served.content == img1
    assert (await client.get(url, headers=other.headers)).status_code == 404
    assert (await client.get(url)).status_code == 404

    # Xóa trang không phải của mình bị từ chối; chủ xóa được (F03.09).
    assert (await client.delete(f"{API}/pages/{pages[0]['id']}", headers=other.headers)).status_code == 404

    # Sửa truyện/chương của mình.
    patched = await client.patch(
        f"{API}/series/{sid}", json={"title_vi": "Hoa Hồng 2"}, headers=owner.headers
    )
    assert patched.json()["title_vi"] == "Hoa Hồng 2"
    patched_ch = await client.patch(
        f"{API}/chapters/{cid}", json={"title": "Chương đầu"}, headers=owner.headers
    )
    assert patched_ch.json()["title"] == "Chương đầu"


async def test_progress_library_rating_and_page_deletion(client: httpx.AsyncClient) -> None:
    """US-NH-16, 61, 62: tiến độ đọc, Thư viện/Yêu thích, chấm sao, xóa trang chuyển tiến độ."""
    user, other = await register(client), await register(client)
    sid = (await _new_series(client, user, "Đang đọc"))["id"]
    cid = (
        await client.post(f"{API}/series/{sid}/chapters", json={"number": 1}, headers=user.headers)
    ).json()["id"]
    up = await client.post(
        f"{API}/chapters/{cid}/pages",
        files=_files(*[(f"{i}.png", png_bytes((i * 40, 5, 5))) for i in range(1, 5)]),
        headers=user.headers,
    )
    page_ids = [r["page"]["id"] for r in up.json()["results"]]
    assert len(page_ids) == 4

    # Tiến độ (F03.12).
    assert (await client.get(f"{API}/reading-progress/continue")).status_code == 401
    bad = await client.put(f"{API}/chapters/{cid}/progress", json={"page_no": 99}, headers=user.headers)
    assert (bad.status_code, error_code(bad)) == (400, "INVALID_PAGE_NUMBER")
    saved = await client.put(
        f"{API}/chapters/{cid}/progress", json={"page_no": 3, "mode": "learn"}, headers=user.headers
    )
    assert saved.json()["page_no"] == 3 and saved.json()["completed"] is False
    # Truyện chưa đọc trong Thư viện: progress null (người khác/Khách không thấy tiến độ của mình).
    await client.put(f"{API}/library/{sid}", headers=user.headers)
    lib_items = (await client.get(f"{API}/library", headers=user.headers)).json()["items"]
    assert lib_items[0]["progress"] is not None  # đã có dòng tiến độ ở trang 3
    unread = await _new_series(client, user, "Chưa đọc")
    assert unread["progress"] is None
    await client.put(f"{API}/library/{unread['id']}", headers=user.headers)
    by_id = {i["id"]: i for i in (await client.get(f"{API}/library", headers=user.headers)).json()["items"]}
    assert by_id[unread["id"]]["progress"] is None
    await client.delete(f"{API}/library/{unread['id']}", headers=user.headers)
    await client.delete(f"{API}/series/{unread['id']}", headers=user.headers)
    part = by_id[sid]["progress"]
    assert (part["chapter_id"], part["page_no"], part["total_pages"], part["mode"]) == (cid, 3, 4, "learn")
    assert (part["completed"], part["pages_total"], part["percent"]) == (False, 4, part["pages_read"] * 25)
    assert part["pages_read"] < 4
    assert (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()["series"][
        "progress"
    ] == part
    cont = (await client.get(f"{API}/reading-progress/continue", headers=user.headers)).json()
    assert [(c["series_id"], c["page_no"], c["total_pages"]) for c in cont] == [(sid, 3, 4)]
    assert cont[0]["page_id"] == page_ids[2]
    resume = (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()["progress"]
    assert (resume["page_no"], resume["mode"]) == (3, "learn")
    assert (await client.get(f"{API}/reading-progress/continue", headers=other.headers)).json() == []

    # Xóa trang đang dừng: tiến độ chuyển tới trang gần nhất còn tồn tại.
    assert (await client.delete(f"{API}/pages/{page_ids[2]}", headers=user.headers)).status_code == 204
    cont = (await client.get(f"{API}/reading-progress/continue", headers=user.headers)).json()
    assert cont[0]["page_no"] == 2
    assert (await client.get(f"{API}/pages/{page_ids[2]}", headers=user.headers)).status_code == 404

    # Thư viện và Yêu thích (F03.13).
    for path in (f"{API}/library/{sid}", f"{API}/library/{sid}/favorite"):
        assert (
            await client.request("PUT", path, headers=other.headers, json={"is_favorite": True})
        ).status_code == 404
    added = await client.put(f"{API}/library/{sid}", headers=user.headers)
    again = await client.put(f"{API}/library/{sid}", headers=user.headers)
    assert added.json()["in_library"] and again.json()["in_library"]
    lib = (await client.get(f"{API}/library", headers=user.headers)).json()
    assert [i["id"] for i in lib["items"]] == [sid] and lib["total"] == 1
    assert (await client.get(f"{API}/library?tab=favorites", headers=user.headers)).json()["total"] == 0
    assert (await client.get(f"{API}/library?tab=reading", headers=user.headers)).json()["total"] == 1
    fav = await client.put(f"{API}/library/{sid}/favorite", json={"is_favorite": True}, headers=user.headers)
    assert fav.json()["is_favorite"] is True
    assert (await client.get(f"{API}/library?tab=favorites", headers=user.headers)).json()["total"] == 1
    assert (await client.get(f"{API}/library", headers=other.headers)).json()["total"] == 0

    # Đọc tới trang cuối của chương → chương xong, truyện hết "đang đọc dở"; đọc đủ trang → tab Đã xong.
    for no in (1, 2, 4):
        await client.put(f"{API}/chapters/{cid}/progress", json={"page_no": no}, headers=user.headers)
    assert (await client.get(f"{API}/reading-progress/continue", headers=user.headers)).json() == []
    done = (await client.get(f"{API}/library?tab=completed", headers=user.headers)).json()
    assert done["total"] == 1
    fin = done["items"][0]["progress"]
    assert (fin["completed"], fin["pages_read"], fin["pages_total"], fin["percent"]) == (True, 3, 3, 100)
    assert (await client.get(f"{API}/library?tab=reading", headers=user.headers)).json()["total"] == 0

    # Chấm sao (F03.14).
    r1 = await client.put(f"{API}/series/{sid}/rating", json={"stars": 4}, headers=user.headers)
    assert r1.json() == {"my_stars": 4, "rating_avg": 4.0, "rating_count": 1}
    r2 = await client.put(f"{API}/series/{sid}/rating", json={"stars": 2}, headers=user.headers)
    assert (r2.json()["rating_avg"], r2.json()["rating_count"]) == (2.0, 1)
    bad_star = await client.put(f"{API}/series/{sid}/rating", json={"stars": 6}, headers=user.headers)
    assert (bad_star.status_code, error_code(bad_star)) == (400, "INVALID_RATING")
    hidden = await client.put(f"{API}/series/{sid}/rating", json={"stars": 3}, headers=other.headers)
    assert hidden.status_code == 404
    detail = (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()
    assert detail["my_rating"] == 2 and detail["series"]["rating_avg"] == 2.0

    # Bỏ khỏi Thư viện không xóa tiến độ.
    assert (await client.delete(f"{API}/library/{sid}", headers=user.headers)).status_code == 204
    assert (await client.get(f"{API}/library", headers=user.headers)).json()["total"] == 0
    assert (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()["progress"] is not None


async def test_admin_publish_trial_guest_access_and_cascade_delete(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-QT-04, 05, US-KH-04: admin đăng công khai, bật đọc thử, Khách đọc thử, xóa tầng."""
    admin = await make_admin(app, client)
    owner = await register(client)

    series = await _new_series(client, owner, "Của người học")
    sid = series["id"]
    cid = (
        await client.post(f"{API}/series/{sid}/chapters", json={"number": 1}, headers=owner.headers)
    ).json()["id"]
    page = (
        await client.post(
            f"{API}/chapters/{cid}/pages",
            files=_files(("p.png", png_bytes((1, 2, 3)))),
            headers=owner.headers,
        )
    ).json()["results"][0]["page"]

    # Admin đọc/sửa được truyện của người khác (F03.11) và công khai hóa (F03.05).
    assert (await client.get(f"{API}/series/{sid}", headers=admin.headers)).status_code == 200
    by_owner = await client.patch(f"{API}/series/{sid}", json={"visibility": "public"}, headers=owner.headers)
    assert (by_owner.status_code, error_code(by_owner)) == (403, "PUBLISH_REQUIRES_ADMIN")
    published = await client.patch(
        f"{API}/series/{sid}", json={"visibility": "public"}, headers=admin.headers
    )
    assert published.status_code == 200 and published.json()["visibility"] == "public"
    assert published.json()["owner_id"] is None

    # Người học chỉ đọc truyện công khai của admin, không sửa/xóa (F03.10).
    assert (await client.get(f"{API}/series/{sid}", headers=owner.headers)).status_code == 200
    forbidden = await client.patch(f"{API}/series/{sid}", json={"title_vi": "x"}, headers=owner.headers)
    assert (forbidden.status_code, error_code(forbidden)) == (403, "PERMISSION_DENIED")
    assert (await client.delete(f"{API}/pages/{page['id']}", headers=owner.headers)).status_code == 403
    listed = (await client.get(f"{API}/series", headers=owner.headers)).json()
    assert sid in [i["id"] for i in listed["items"]]

    # Khách: thấy truyện nhưng chưa có chương đọc thử → chương bị chặn (F03.03).
    guest_detail = (await client.get(f"{API}/series/{sid}")).json()
    assert guest_detail["chapters"] == []
    locked = await client.get(f"{API}/chapters/{cid}")
    assert (locked.status_code, error_code(locked)) == (401, "LOGIN_REQUIRED")
    assert (await client.get(page["original_url"])).status_code == 404
    assert sid not in [i["id"] for i in (await client.get(f"{API}/series")).json()["items"]]

    # Admin bật cờ đọc thử; Khách đọc được chương (chỉ trang đã xử lý xong) và xem ảnh của chương.
    toggled = await client.patch(f"{API}/chapters/{cid}", json={"is_trial": True}, headers=admin.headers)
    assert toggled.json()["is_trial"] is True
    no_perm = await client.patch(f"{API}/chapters/{cid}", json={"is_trial": False}, headers=owner.headers)
    assert no_perm.status_code in (403, 404)
    guest_chapter = await client.get(f"{API}/chapters/{cid}")
    assert guest_chapter.status_code == 200 and guest_chapter.json()["pages"] == []
    assert [c["id"] for c in (await client.get(f"{API}/series/{sid}")).json()["chapters"]] == [cid]
    assert (await client.get(page["original_url"])).status_code == 200
    assert sid in [i["id"] for i in (await client.get(f"{API}/series")).json()["items"]]

    # Xóa tầng: admin xóa truyện → chương, trang, tệp biến mất (F03.11).
    assert (await client.delete(f"{API}/series/{sid}", headers=admin.headers)).status_code == 204
    assert (await client.get(f"{API}/series/{sid}", headers=admin.headers)).status_code == 404
    assert (await client.get(f"{API}/pages/{page['id']}", headers=admin.headers)).status_code == 404
    assert (await client.get(page["original_url"], headers=admin.headers)).status_code == 404
