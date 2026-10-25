"""M01 Tài khoản — F01.07 hồ sơ, F01.08 đổi mật khẩu (US-NH-04, US-NH-05)."""

from __future__ import annotations

import httpx
import pytest

from tests.helpers import error_code, login, register

pytestmark = pytest.mark.integration


async def test_profile_shows_own_data_without_password(client: httpx.AsyncClient) -> None:
    account = await register(client, display_name="  Lam Hiên Vũ  ")
    res = await client.get("/api/v1/account/me", headers=account.headers)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == account.email and body["display_name"] == "Lam Hiên Vũ"
    assert "password" not in res.text and "hash" not in res.text


async def test_update_profile_changes_only_given_fields(client: httpx.AsyncClient) -> None:
    account = await register(client)
    res = await client.patch(
        "/api/v1/account/me",
        json={"display_name": "Tên mới", "chinese_name": "轩宇", "show_email": False},
        headers=account.headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert (body["display_name"], body["chinese_name"], body["show_email"], body["show_join_date"]) == (
        "Tên mới",
        "轩宇",
        False,
        True,
    )
    again = await client.patch("/api/v1/account/me", json={"show_join_date": False}, headers=account.headers)
    assert again.json()["display_name"] == "Tên mới" and again.json()["show_join_date"] is False


async def test_update_profile_rejects_blank_display_name(client: httpx.AsyncClient) -> None:
    account = await register(client)
    res = await client.patch("/api/v1/account/me", json={"display_name": "   "}, headers=account.headers)
    assert res.status_code == 400 and error_code(res) == "DISPLAY_NAME_REQUIRED"


async def test_change_password_keeps_current_session_and_revokes_others(client: httpx.AsyncClient) -> None:
    this_device = await register(client)
    other_device = await login(client, this_device)
    res = await client.post(
        "/api/v1/account/change-password",
        json={"current_password": this_device.password, "new_password": "mat-khau-moi-99"},
        headers=this_device.headers,
    )
    assert res.status_code == 204
    assert (await client.get("/api/v1/account/me", headers=this_device.headers)).status_code == 200
    assert (await client.get("/api/v1/account/me", headers=other_device.headers)).status_code == 401
    ok = await client.post(
        "/api/v1/auth/login", json={"email": this_device.email, "password": "mat-khau-moi-99"}
    )
    assert ok.status_code == 200


@pytest.mark.parametrize(
    ("current", "new", "code"),
    [
        ("sai-mat-khau-hien-tai", "mat-khau-moi-99", "WRONG_CURRENT_PASSWORD"),
        ("matkhau-dung-123", "ngan", "WEAK_PASSWORD"),
        ("matkhau-dung-123", "matkhau-dung-123", "SAME_PASSWORD"),
    ],
)
async def test_change_password_validations(
    client: httpx.AsyncClient, current: str, new: str, code: str
) -> None:
    account = await register(client)
    res = await client.post(
        "/api/v1/account/change-password",
        json={"current_password": current, "new_password": new},
        headers=account.headers,
    )
    assert res.status_code == 400 and error_code(res) == code
