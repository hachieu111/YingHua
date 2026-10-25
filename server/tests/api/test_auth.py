"""M01 Xác thực — F01.01…F01.06, F01.09 (US-KH-02/03/06, US-NH-01/02/03)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from tests.helpers import PASSWORD, error_code, login, make_admin, register, unique_email

pytestmark = pytest.mark.integration


async def test_register_creates_learner_with_session(client: httpx.AsyncClient) -> None:
    """US-KH-02 TC1: tài khoản mới là Người học, được đăng nhập ngay; tên hiển thị mặc định từ email."""
    local = f"Hoc.Vien.{uuid.uuid4().hex[:10]}"
    res = await client.post(
        "/api/v1/auth/register", json={"email": f"{local}@Example.com", "password": PASSWORD}
    )
    assert res.status_code == 201
    user = res.json()["user"]
    assert (user["email"], user["role"], user["status"]) == (f"{local.lower()}@example.com", "user", "active")
    assert user["display_name"] == local.lower()
    assert "password" not in res.text and "hash" not in res.text
    assert res.json()["tokens"]["token_type"] == "bearer"


async def test_register_rejects_duplicate_email_ignoring_case(client: httpx.AsyncClient) -> None:
    account = await register(client)
    res = await client.post(
        "/api/v1/auth/register", json={"email": account.email.upper(), "password": PASSWORD}
    )
    assert res.status_code == 409
    assert res.json()["error"]["message"] == "Email đã được sử dụng"


@pytest.mark.parametrize("password", ["1234567", ""])
async def test_register_rejects_short_password(client: httpx.AsyncClient, password: str) -> None:
    res = await client.post("/api/v1/auth/register", json={"email": unique_email(), "password": password})
    assert res.status_code == 400
    assert res.json()["error"]["message"] == "Mật khẩu tối thiểu 8 ký tự"


async def test_register_rejects_invalid_email(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/v1/auth/register", json={"email": "khong-phai-email", "password": PASSWORD})
    assert res.status_code == 422


async def test_login_wrong_password_and_unknown_email_share_one_message(client: httpx.AsyncClient) -> None:
    """US-KH-03: không lộ email có tồn tại hay không."""
    account = await register(client)
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": account.email, "password": "sai-mat-khau-1"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": unique_email(), "password": "sai-mat-khau-1"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert error_code(wrong) == "INVALID_CREDENTIALS"


async def test_login_blocked_after_too_many_failures(client: httpx.AsyncClient) -> None:
    account = await register(client)
    for _ in range(5):
        res = await client.post(
            "/api/v1/auth/login", json={"email": account.email, "password": "sai-mat-khau-1"}
        )
        assert res.status_code == 401
    res = await client.post("/api/v1/auth/login", json={"email": account.email, "password": account.password})
    assert res.status_code == 429


async def test_locked_account_reveals_lock_only_with_correct_password(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    admin = await make_admin(app, client)
    victim = await register(client)
    res = await client.post(
        f"/api/v1/admin/users/{victim.id}/lock", json={"reason": "Vi phạm"}, headers=admin.headers
    )
    assert res.status_code == 200
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": victim.email, "password": "sai-mat-khau-1"}
    )
    right = await client.post("/api/v1/auth/login", json={"email": victim.email, "password": victim.password})
    assert error_code(wrong) == "INVALID_CREDENTIALS"
    assert right.status_code == 403 and error_code(right) == "ACCOUNT_LOCKED"


async def test_protected_route_requires_valid_token(client: httpx.AsyncClient) -> None:
    """F01.09: không có token hoặc token giả đều bị từ chối theo định dạng lỗi chuẩn."""
    missing = await client.get("/api/v1/account/me")
    forged = await client.get("/api/v1/account/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert missing.status_code == forged.status_code == 401
    assert error_code(missing) == "UNAUTHENTICATED"


async def test_refresh_rotates_token_and_reuse_revokes_whole_session(client: httpx.AsyncClient) -> None:
    """US-NH-01: làm mới xoay vòng; dùng lại mã cũ thì cả phiên bị thu hồi."""
    account = await register(client)
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": account.refresh})
    assert first.status_code == 200
    new_refresh = first.json()["tokens"]["refresh_token"]
    new_access = first.json()["tokens"]["access_token"]
    assert new_refresh != account.refresh

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": account.refresh})
    assert reuse.status_code == 401 and error_code(reuse) == "SESSION_EXPIRED"
    # Cả mã mới và mã truy cập của phiên đó đều mất hiệu lực.
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})).status_code == 401
    me = await client.get("/api/v1/account/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 401


async def test_refresh_rejects_unknown_token(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": "khong-ton-tai"})
    assert res.status_code == 401 and error_code(res) == "SESSION_EXPIRED"


async def test_refresh_refuses_locked_account(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await make_admin(app, client)
    victim = await register(client)
    await client.post(f"/api/v1/admin/users/{victim.id}/lock", json={}, headers=admin.headers)
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": victim.refresh})
    assert res.status_code in (401, 403)


async def test_logout_revokes_only_current_device(client: httpx.AsyncClient) -> None:
    """US-NH-02: thiết bị khác giữ nguyên phiên."""
    phone = await register(client)
    laptop = await login(client, phone)
    assert (await client.post("/api/v1/auth/logout", headers=phone.headers)).status_code == 204
    assert (await client.get("/api/v1/account/me", headers=phone.headers)).status_code == 401
    assert (await client.get("/api/v1/account/me", headers=laptop.headers)).status_code == 200


async def test_logout_all_revokes_every_session_and_reports_count(client: httpx.AsyncClient) -> None:
    """US-NH-03."""
    a = await register(client)
    b = await login(client, a)
    c = await login(client, a)
    res = await client.post("/api/v1/auth/logout-all", headers=a.headers)
    assert res.status_code == 200 and res.json() == {"revoked_sessions": 3}
    for device in (a, b, c):
        assert (await client.get("/api/v1/account/me", headers=device.headers)).status_code == 401


def _reset_token(outbox: Path) -> str:
    files = sorted(outbox.glob("*.txt"))
    assert files, "không có email nào được gửi"
    match = re.search(r"reset_token=([^\s]+)", files[-1].read_text(encoding="utf-8"))
    assert match
    return match.group(1)


async def test_forgot_and_reset_password_flow(client: httpx.AsyncClient, outbox_dir: Path) -> None:
    """US-KH-06: liên kết dùng một lần, đặt lại xong thì mọi phiên cũ bị đăng xuất."""
    account = await register(client)
    res = await client.post("/api/v1/auth/forgot-password", json={"email": account.email})
    assert res.status_code == 202
    assert res.json()["message"] == "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn"
    token = _reset_token(outbox_dir)

    short = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "ngan"})
    assert short.status_code == 400
    ok = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "mat-khau-moi-99"}
    )
    assert ok.status_code == 204

    assert (await client.get("/api/v1/account/me", headers=account.headers)).status_code == 401
    old = await client.post("/api/v1/auth/login", json={"email": account.email, "password": account.password})
    new = await client.post(
        "/api/v1/auth/login", json={"email": account.email, "password": "mat-khau-moi-99"}
    )
    assert old.status_code == 401 and new.status_code == 200

    again = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "mat-khau-moi-77"}
    )
    assert again.status_code == 400 and error_code(again) == "RESET_LINK_INVALID"


async def test_forgot_password_does_not_reveal_unknown_email(
    client: httpx.AsyncClient, outbox_dir: Path
) -> None:
    res = await client.post("/api/v1/auth/forgot-password", json={"email": unique_email()})
    assert res.status_code == 202
    assert res.json()["message"] == "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn"
    assert not outbox_dir.exists() or not list(outbox_dir.glob("*.txt"))


async def test_reset_password_rejects_garbage_token(client: httpx.AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/reset-password", json={"token": "rac", "new_password": "mat-khau-moi-99"}
    )
    assert res.status_code == 400 and error_code(res) == "RESET_LINK_INVALID"
