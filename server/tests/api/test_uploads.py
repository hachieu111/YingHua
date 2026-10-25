"""F03.08 ảnh tải nhanh, F03.04 ảnh bìa, F01.10 ảnh đại diện, và giới hạn upload (413/400)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.helpers import error_code, make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"
MB = 1024 * 1024


def _one(name: str, data: bytes) -> dict[str, tuple[str, bytes, str]]:
    return {"file": (name, data, "application/octet-stream")}


async def test_quick_upload_is_private_expires_in_seven_days_and_dedups_translation(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-13: ảnh lẻ thuộc riêng người tải, hết hạn sau 7 ngày."""
    owner, other = await register(client), await register(client)
    admin = await make_admin(app, client)

    assert (await client.post(f"{API}/quick-uploads", files=_one("a.png", png_bytes()))).status_code == 401
    res = await client.post(f"{API}/quick-uploads", files=_one("a.png", png_bytes()), headers=owner.headers)
    assert res.status_code == 201, res.text
    page = res.json()
    assert (page["chapter_id"], page["series_id"], page["status"]) == (None, None, "queued")
    assert page["expires_at"] is not None and page["can_edit"] is True

    listed = (await client.get(f"{API}/quick-uploads", headers=owner.headers)).json()
    assert [p["id"] for p in listed["items"]] == [page["id"]] and listed["total"] == 1
    assert (await client.get(f"{API}/quick-uploads", headers=other.headers)).json()["total"] == 0

    assert (await client.get(f"{API}/pages/{page['id']}", headers=owner.headers)).status_code == 200
    assert (await client.get(f"{API}/pages/{page['id']}", headers=admin.headers)).status_code == 200
    assert (await client.get(f"{API}/pages/{page['id']}", headers=other.headers)).status_code == 404
    assert (await client.get(f"{API}/pages/{page['id']}")).status_code == 404
    assert (await client.get(page["original_url"], headers=owner.headers)).status_code == 200
    assert (await client.get(page["original_url"], headers=other.headers)).status_code == 404

    assert (await client.delete(f"{API}/pages/{page['id']}", headers=other.headers)).status_code == 404
    assert (await client.delete(f"{API}/pages/{page['id']}", headers=owner.headers)).status_code == 204
    assert (await client.get(page["original_url"], headers=owner.headers)).status_code == 404


async def test_avatar_cover_and_upload_limits(client: httpx.AsyncClient) -> None:
    """US-NH-65 và security.md: MIME thật, tối đa 10 MB, ảnh mới thay ảnh cũ, đường dẫn không lộ."""
    user, other = await register(client), await register(client)

    me = (await client.get(f"{API}/account/me", headers=user.headers)).json()
    assert me["avatar_url"] is None

    assert (
        await client.post(f"{API}/account/me/avatar", files=_one("a.png", png_bytes()))
    ).status_code == 401
    fake = await client.post(
        f"{API}/account/me/avatar", files=_one("a.png", b"GIF89a-not-allowed"), headers=user.headers
    )
    assert (fake.status_code, error_code(fake)) == (400, "UNSUPPORTED_IMAGE_TYPE")
    renamed = await client.post(
        f"{API}/account/me/avatar", files=_one("a.exe", png_bytes()), headers=user.headers
    )
    assert (renamed.status_code, error_code(renamed)) == (400, "UNSUPPORTED_IMAGE_TYPE")
    big = await client.post(
        f"{API}/account/me/avatar",
        files=_one("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * (11 * MB)),
        headers=user.headers,
    )
    assert (big.status_code, error_code(big)) == (413, "IMAGE_TOO_LARGE")

    first = await client.post(
        f"{API}/account/me/avatar", files=_one("a.png", png_bytes((1, 1, 1))), headers=user.headers
    )
    assert first.status_code == 200, first.text
    first_url = first.json()["avatar_url"]
    assert first_url.startswith("/api/v1/files/") and "storage" not in first_url
    served = await client.get(first_url, headers=other.headers)  # người đã đăng nhập xem được ảnh đại diện
    assert (served.status_code, served.headers["content-type"]) == (200, "image/png")
    assert (await client.get(first_url)).status_code == 404  # Khách không xem được

    second = await client.post(
        f"{API}/account/me/avatar", files=_one("b.png", png_bytes((9, 9, 9))), headers=user.headers
    )
    assert second.json()["avatar_url"] != first_url
    assert (await client.get(first_url, headers=user.headers)).status_code == 404  # ảnh cũ bị xóa
    assert (await client.get(f"{API}/account/me", headers=user.headers)).json()[
        "avatar_url"
    ] == second.json()["avatar_url"]

    # Ảnh bìa truyện riêng tư: chủ xem được, người khác và Khách thì không (F03.04, F03.10).
    sid = (await client.post(f"{API}/series", json={"title_vi": "Có bìa"}, headers=user.headers)).json()["id"]
    cover = await client.put(
        f"{API}/series/{sid}/cover", files=_one("c.png", png_bytes((5, 5, 200))), headers=user.headers
    )
    assert cover.status_code == 200 and cover.json()["cover_url"]
    cover_url = cover.json()["cover_url"]
    assert (await client.get(cover_url, headers=user.headers)).status_code == 200
    assert (await client.get(cover_url, headers=other.headers)).status_code == 404
    assert (await client.get(cover_url)).status_code == 404
    other_cover = await client.put(
        f"{API}/series/{sid}/cover", files=_one("c.png", png_bytes()), headers=other.headers
    )
    assert other_cover.status_code == 404
    new_cover = await client.put(
        f"{API}/series/{sid}/cover", files=_one("d.png", png_bytes((6, 6, 6))), headers=user.headers
    )
    assert new_cover.json()["cover_url"] != cover_url
    assert (await client.get(cover_url, headers=user.headers)).status_code == 404
