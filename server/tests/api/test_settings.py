"""M02 Cài đặt cá nhân — F02.01…F02.03 (US-NH-06, US-NH-07, US-NH-08)."""

from __future__ import annotations

import httpx
import pytest

from tests.helpers import error_code, register

pytestmark = pytest.mark.integration


async def test_new_user_gets_defaults(client: httpx.AsyncClient) -> None:
    account = await register(client)
    res = await client.get("/api/v1/settings", headers=account.headers)
    assert res.status_code == 200
    assert res.json() == {
        "hsk_level": None,
        "default_mode": "read",
        "tts_voice": None,
        "learning_goal": None,
        "weekly_page_goal": None,
        "show_xianxia": True,
        "bubble_font_scale": 100,
        "reminder_enabled": False,
        "reminder_time": None,
        "timezone": "Asia/Ho_Chi_Minh",
        "show_on_leaderboard": True,
        "dismissed_tours": [],
    }


async def test_dismissed_tours_save_reset_dedupe_and_reject_unknown(client: httpx.AsyncClient) -> None:
    """F02.05: lưu "không nhắc lại" ở máy chủ, thay toàn bộ, bỏ trùng, khóa lạ 422, tách theo người."""
    account = await register(client)
    other = await register(client)
    res = await client.patch(
        "/api/v1/settings",
        json={"dismissed_tours": ["reader", "home", "reader", "upload"]},
        headers=account.headers,
    )
    assert res.status_code == 200 and res.json()["dismissed_tours"] == ["reader", "home", "upload"]
    again = await client.get("/api/v1/settings", headers=account.headers)
    assert again.json()["dismissed_tours"] == ["reader", "home", "upload"]
    assert (await client.get("/api/v1/settings", headers=other.headers)).json()["dismissed_tours"] == []

    for bad in (["unknown"], ["home", "x"], "home", [1]):
        res = await client.patch("/api/v1/settings", json={"dismissed_tours": bad}, headers=account.headers)
        assert res.status_code == 422, res.text
    assert (await client.get("/api/v1/settings", headers=account.headers)).json()["dismissed_tours"] == [
        "reader",
        "home",
        "upload",
    ]

    res = await client.patch("/api/v1/settings", json={"dismissed_tours": []}, headers=account.headers)
    assert res.status_code == 200 and res.json()["dismissed_tours"] == []
    assert (await client.get("/api/v1/settings", headers=account.headers)).json()["dismissed_tours"] == []


async def test_show_on_leaderboard_toggles_and_rejects_non_boolean(client: httpx.AsyncClient) -> None:
    """US-NH-89 TC1, TC4: cờ ẩn danh mặc định bật, lưu được, không phải boolean thì 422."""
    account = await register(client)
    res = await client.patch("/api/v1/settings", json={"show_on_leaderboard": False}, headers=account.headers)
    assert res.status_code == 200 and res.json()["show_on_leaderboard"] is False
    again = await client.get("/api/v1/settings", headers=account.headers)
    assert again.json()["show_on_leaderboard"] is False
    for bad in ("no", 0, None):
        res = await client.patch(
            "/api/v1/settings", json={"show_on_leaderboard": bad}, headers=account.headers
        )
        assert res.status_code in (400, 422), res.text
    assert (await client.get("/api/v1/settings", headers=account.headers)).json()[
        "show_on_leaderboard"
    ] is False


async def test_settings_require_login(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/settings")).status_code == 401


async def test_update_hsk_mode_voice_and_persist(client: httpx.AsyncClient) -> None:
    account = await register(client)
    res = await client.patch(
        "/api/v1/settings",
        json={
            "hsk_level": 5,
            "default_mode": "learn",
            "tts_voice": "zh-CN-XiaoxiaoNeural",
            "learning_goal": "both",
        },
        headers=account.headers,
    )
    assert res.status_code == 200
    saved = (await client.get("/api/v1/settings", headers=account.headers)).json()
    assert (saved["hsk_level"], saved["default_mode"], saved["tts_voice"], saved["learning_goal"]) == (
        5,
        "learn",
        "zh-CN-XiaoxiaoNeural",
        "both",
    )


async def test_partial_update_keeps_other_fields_and_null_clears_hsk(client: httpx.AsyncClient) -> None:
    account = await register(client)
    await client.patch(
        "/api/v1/settings", json={"hsk_level": 3, "default_mode": "learn"}, headers=account.headers
    )
    await client.patch("/api/v1/settings", json={"hsk_level": None}, headers=account.headers)
    saved = (await client.get("/api/v1/settings", headers=account.headers)).json()
    assert saved["hsk_level"] is None and saved["default_mode"] == "learn"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"hsk_level": 0}, "hsk_level"),
        ({"hsk_level": 10}, "hsk_level"),
        ({"default_mode": "khac"}, "default_mode"),
        ({"tts_voice": "giong khong hop le"}, "tts_voice"),
        ({"learning_goal": "khac"}, "learning_goal"),
        ({"weekly_page_goal": 0}, "weekly_page_goal"),
    ],
)
async def test_invalid_values_are_rejected(
    client: httpx.AsyncClient, payload: dict[str, object], field: str
) -> None:
    account = await register(client)
    res = await client.patch("/api/v1/settings", json=payload, headers=account.headers)
    assert res.status_code == 400 and error_code(res) == "INVALID_INPUT"
    assert res.json()["error"]["details"]["field"] == field


async def test_settings_are_private_to_each_user(client: httpx.AsyncClient) -> None:
    a, b = await register(client), await register(client)
    await client.patch("/api/v1/settings", json={"hsk_level": 7}, headers=a.headers)
    assert (await client.get("/api/v1/settings", headers=b.headers)).json()["hsk_level"] is None
