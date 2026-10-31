"""M17 VIP & Phần thưởng qua API: ví, VIP, đọc truyện VIP, vé, cửa hàng, khung, quản trị (F17.01-F17.10)."""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from app.modules.rewards.application.public import RemindVipExpiryUseCase
from app.modules.rewards.infrastructure.public import SqlRewardsUnitOfWork, build_reward_notifier
from tests.helpers import Account, error_code, make_admin, png_bytes, register

pytestmark = pytest.mark.integration

API = "/api/v1"


def _png() -> bytes:
    return png_bytes((random.randrange(256), random.randrange(256), random.randrange(256)))


async def _wallet(client: httpx.AsyncClient, who: Account) -> dict[str, Any]:
    res = await client.get(f"{API}/rewards/wallet", headers=who.headers)
    assert res.status_code == 200, res.text
    data: dict[str, Any] = res.json()
    return data


async def _adjust(
    client: httpx.AsyncClient,
    admin: Account,
    user: Account,
    currency: str,
    amount: int,
    reason: str = "thử",
    request_id: str | None = None,
) -> httpx.Response:
    return await client.post(
        f"{API}/admin/users/{user.id}/wallet-adjustments",
        json={
            "currency": currency,
            "amount": amount,
            "reason": reason,
            "request_id": request_id or str(uuid.uuid4()),
        },
        headers=admin.headers,
    )


async def _grant_vip(
    client: httpx.AsyncClient, admin: Account, user: Account, days: int, request_id: str | None = None
) -> httpx.Response:
    return await client.post(
        f"{API}/admin/users/{user.id}/vip-grants",
        json={"days": days, "reason": "thử", "request_id": request_id or str(uuid.uuid4())},
        headers=admin.headers,
    )


async def _revoke_vip(
    client: httpx.AsyncClient, admin: Account, user: Account, request_id: str | None = None
) -> httpx.Response:
    return await client.post(
        f"{API}/admin/users/{user.id}/vip-grants",
        json={"revoke": True, "reason": "thu hồi để thử", "request_id": request_id or str(uuid.uuid4())},
        headers=admin.headers,
    )


async def _drop_vip(client: httpx.AsyncClient, admin: Account, user: Account) -> None:
    """Tài khoản mới có sẵn 3 ngày VIP (quà chào mừng); thu hồi để test hành vi của người không VIP."""
    res = await _revoke_vip(client, admin, user)
    assert res.status_code == 200, res.text
    assert res.json()["vip"]["is_active"] is False


async def _non_vip_user(client: httpx.AsyncClient, admin: Account) -> Account:
    user = await register(client)
    await _drop_vip(client, admin, user)
    return user


async def _notification_kinds(client: httpx.AsyncClient, who: Account) -> list[str]:
    res = await client.get(f"{API}/notifications?size=50", headers=who.headers)
    return [n["kind"] for n in res.json()["items"]]


# ---- ví, VIP, quà chào mừng ------------------------------------------------------------------------------


async def test_new_account_gets_three_vip_days_once_with_notification_and_empty_wallet(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-94 TC1, US-NH-93 TC3: 3 ngày VIP lúc đăng ký + thông báo; xu, vé bằng 0; lịch sử có dòng quà."""
    user = await register(client)
    wallet = await _wallet(client, user)
    assert (wallet["coin_balance"], wallet["ticket_balance"], wallet["equipped_frame"]) == (0, 0, None)
    assert wallet["vip"]["is_active"] is True and wallet["vip"]["days_left"] == 3

    me = (await client.get(f"{API}/vip/me", headers=user.headers)).json()
    assert me["is_active"] and me["can_read_vip_series"] and me["unlocked_series_count"] == 0
    assert "vip_granted" in await _notification_kinds(client, user)

    ledger = (await client.get(f"{API}/rewards/wallet/ledger", headers=user.headers)).json()
    assert ledger["total"] == 1
    entry = ledger["items"][0]
    assert (entry["currency"], entry["amount"], entry["reason"]) == ("vip_days", 3, "welcome")
    assert entry["reason_label"] == "Quà chào mừng" and entry["vip_until_after"] is not None
    assert "actor_id" not in entry  # không lộ mã quản trị viên cho Người học

    # Bốn hạn mức AI hiệu lực khi VIP (US-NH-95 TC1).
    assert me["ai_limits"] == {
        "quiz_daily_llm_limit": 10,
        "ai_note_daily_limit": 40,
        "grammar_daily_limit": 60,
        "mistake_review_daily_limit": 40,
    }


async def test_registration_succeeds_even_if_welcome_gift_fails(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-94 TC6: tặng quà lỗi thì tài khoản vẫn được tạo."""

    class Broken:
        async def grant_welcome(self, user_id: int) -> None:
            raise RuntimeError("CSDL tạm lỗi")

    app.state.container.welcome_gift = Broken()
    user = await register(client)
    assert (await client.get(f"{API}/account/me", headers=user.headers)).status_code == 200
    assert (await _wallet(client, user))["vip"]["is_active"] is False


async def test_rewards_endpoints_need_login_and_admin_endpoints_need_admin_role(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """Phân quyền: Khách 401, Người học 403 ở API quản trị, người dùng đích không tồn tại 404."""
    user, admin = await register(client), await make_admin(app, client)
    for path in (
        "/rewards/wallet",
        "/rewards/wallet/ledger",
        "/rewards/shop/items",
        "/rewards/frames",
        "/vip/me",
    ):
        assert (await client.get(f"{API}{path}")).status_code == 401, path
    assert (await client.post(f"{API}/vip/unlocks", json={})).status_code == 401
    assert (await client.post(f"{API}/rewards/redemptions", json={})).status_code == 401

    body = {"currency": "coin", "amount": 5, "reason": "x", "request_id": str(uuid.uuid4())}
    assert (await client.get(f"{API}/admin/reward-items", headers=user.headers)).status_code == 403
    assert (
        await client.put(f"{API}/admin/series/1/vip", json={"is_vip": True}, headers=user.headers)
    ).status_code == 403
    assert (await client.get(f"{API}/admin/users/{user.id}/rewards", headers=user.headers)).status_code == 403
    vip_body = {"days": 3, "reason": "x", "request_id": str(uuid.uuid4())}
    for path, payload in (("wallet-adjustments", body), ("vip-grants", vip_body)):
        res = await client.post(f"{API}/admin/users/{user.id}/{path}", json=payload, headers=user.headers)
        assert res.status_code == 403, path
    ghost = await client.get(f"{API}/admin/users/999999999/rewards", headers=admin.headers)
    assert (ghost.status_code, error_code(ghost)) == (404, "USER_NOT_FOUND")
    assert (
        await client.get(f"{API}/rewards/wallet/ledger?currency=gold", headers=user.headers)
    ).status_code == 422


async def test_admin_wallet_adjustment_rules_ledger_and_audit(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-QT-18 TC1-TC6, US-NH-93 TC2, TC4."""
    admin, user = await make_admin(app, client), await register(client)
    ok = await _adjust(client, admin, user, "coin", 100, "thưởng bù sự cố")
    assert ok.status_code == 200 and ok.json()["coin_balance"] == 100

    negative = await _adjust(client, admin, user, "coin", -200)
    assert (negative.status_code, error_code(negative)) == (409, "WALLET_NEGATIVE")
    assert (await _wallet(client, user))["coin_balance"] == 100

    for payload in (
        {"currency": "coin", "amount": 0, "reason": "x"},
        {"currency": "coin", "amount": 100_001, "reason": "x"},
        {"currency": "ticket", "amount": 11, "reason": "x"},
        {"currency": "coin", "amount": 5, "reason": ""},
        {"currency": "vip_days", "amount": 5, "reason": "x"},
    ):
        res = await client.post(
            f"{API}/admin/users/{user.id}/wallet-adjustments",
            json={**payload, "request_id": str(uuid.uuid4())},
            headers=admin.headers,
        )
        assert res.status_code == 422, payload
    no_request_id = {"currency": "coin", "amount": 5, "reason": "x"}
    missing = await client.post(
        f"{API}/admin/users/{user.id}/wallet-adjustments", json=no_request_id, headers=admin.headers
    )
    assert missing.status_code == 422  # request_id là bắt buộc (F17.10)
    assert (await _adjust(client, admin, user, "ticket", 99)).status_code == 422

    assert (await _adjust(client, admin, user, "coin", -40, "thu xu gian lận")).status_code == 200
    ledger = (await client.get(f"{API}/rewards/wallet/ledger?currency=coin", headers=user.headers)).json()
    assert [(e["amount"], e["balance_after"]) for e in ledger["items"]] == [(-40, 60), (100, 100)]
    assert ledger["items"][0]["reason_label"] == "Điều chỉnh bởi quản trị viên"
    assert ledger["items"][0]["note"] == "thu xu gian lận"
    assert "wallet_adjusted" in await _notification_kinds(client, user)

    # Tự điều chỉnh cho chính mình được phép; nhật ký ghi cả người thực hiện lẫn người nhận (TC4).
    assert (await _adjust(client, admin, admin, "coin", 10, "tự thử")).status_code == 200
    audit = (
        await client.get(
            f"{API}/admin/audit-logs?action=rewards.wallet_adjusted&size=50", headers=admin.headers
        )
    ).json()
    mine = [a for a in audit["items"] if a["target_id"] == admin.id]
    assert len(mine) == 1 and mine[0]["admin"]["id"] == admin.id and mine[0]["details"]["amount"] == 10
    assert sum(1 for a in audit["items"] if a["target_id"] == user.id) == 2

    view = (await client.get(f"{API}/admin/users/{user.id}/rewards?size=1", headers=admin.headers)).json()
    assert view["wallet"]["coin_balance"] == 60 and view["ledger"]["total"] >= 3
    assert len(view["ledger"]["items"]) == 1 and "actor_id" in view["ledger"]["items"][0]


async def test_admin_vip_grant_stacks_and_revoke_resets(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-QT-18 TC2: cấp cộng dồn; thu hồi đưa VIP về hiện tại; thu khi không VIP bị từ chối."""
    admin, user = await make_admin(app, client), await register(client)
    before = (await _wallet(client, user))["vip"]["days_left"]
    granted = await _grant_vip(client, admin, user, 7)
    assert granted.status_code == 200 and granted.json()["vip"]["days_left"] == before + 7
    assert "vip_granted" in await _notification_kinds(client, user)
    await _drop_vip(client, admin, user)
    again = await _revoke_vip(client, admin, user)
    assert (again.status_code, error_code(again)) == (409, "VIP_NOT_ACTIVE")
    for payload in ({"days": 366, "reason": "x"}, {"days": 3}, {"reason": "x"}):
        res = await client.post(
            f"{API}/admin/users/{user.id}/vip-grants",
            json={**payload, "request_id": str(uuid.uuid4())},
            headers=admin.headers,
        )
        assert res.status_code in (422, 400), payload
    no_request_id = await client.post(
        f"{API}/admin/users/{user.id}/vip-grants", json={"days": 3, "reason": "x"}, headers=admin.headers
    )
    assert no_request_id.status_code == 422  # request_id là bắt buộc (F17.10)


async def test_admin_double_click_wallet_vip_and_revoke_apply_once(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-QT-18 / F17.10: gửi lại cùng request_id (xu, vé, cấp VIP, thu hồi VIP) không cộng/thu lần hai."""
    admin, user = await make_admin(app, client), await register(client)
    for currency, amount in (("coin", 100), ("ticket", 2)):
        rid = str(uuid.uuid4())
        first = await _adjust(client, admin, user, currency, amount, request_id=rid)
        replay = await _adjust(client, admin, user, currency, amount, request_id=rid)
        assert (first.status_code, replay.status_code) == (200, 200), replay.text
        assert replay.json() == first.json()
    wallet = await _wallet(client, user)
    assert (wallet["coin_balance"], wallet["ticket_balance"]) == (100, 2)

    days_before = wallet["vip"]["days_left"]
    rid = str(uuid.uuid4())
    granted = await _grant_vip(client, admin, user, 5, request_id=rid)
    replay = await _grant_vip(client, admin, user, 5, request_id=rid)
    assert granted.status_code == replay.status_code == 200
    assert (await _wallet(client, user))["vip"]["days_left"] == days_before + 5

    rid = str(uuid.uuid4())
    assert (await _revoke_vip(client, admin, user, rid)).status_code == 200
    replay = await _revoke_vip(client, admin, user, rid)  # cùng mã: kết quả cũ, không báo "chưa có VIP"
    assert replay.status_code == 200 and replay.json()["vip"]["is_active"] is False

    audit = (
        await client.get(
            f"{API}/admin/audit-logs?action=rewards.wallet_adjusted&size=50", headers=admin.headers
        )
    ).json()
    assert sum(1 for a in audit["items"] if a["target_id"] == user.id) == 2
    for action, expected in (("rewards.vip_granted", 1), ("rewards.vip_revoked", 1)):
        logs = (
            await client.get(f"{API}/admin/audit-logs?action={action}&size=50", headers=admin.headers)
        ).json()
        assert sum(1 for a in logs["items"] if a["target_id"] == user.id) == expected, action
    ledger = (await client.get(f"{API}/rewards/wallet/ledger?size=50", headers=user.headers)).json()
    assert ledger["total"] == 1 + 1 + 1 + 1 + 1  # quà chào mừng, xu, vé, cấp VIP, thu hồi VIP


# ---- cửa hàng đổi thưởng ----------------------------------------------------------------------------------


async def test_shop_redeem_spends_coins_stacks_vip_and_double_click_charges_once(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-98 TC1-TC4: danh mục, đổi VIP cộng dồn, thiếu xu, bấm đúp chỉ trừ một lần."""
    admin, user = await make_admin(app, client), await register(client)
    items = (await client.get(f"{API}/rewards/shop/items", headers=user.headers)).json()
    by_code = {i["code"]: i for i in items}
    assert {"vip_1d", "vip_7d", "vip_ticket", "frame_bamboo", "frame_ink"} <= set(by_code)
    assert all(i["affordable"] is False for i in items)  # chưa có xu
    assert not any(i["code"] in {"sakura_gold", "vip_sakura", "spring_petal"} for i in items)

    poor = await client.post(
        f"{API}/rewards/redemptions",
        json={"item_id": by_code["vip_1d"]["id"], "request_id": str(uuid.uuid4())},
        headers=user.headers,
    )
    assert (poor.status_code, error_code(poor)) == (409, "NOT_ENOUGH_COINS")
    assert poor.json()["error"]["details"]["missing"] == by_code["vip_1d"]["price_coins"]

    await _adjust(client, admin, user, "coin", 800)
    days_before = (await _wallet(client, user))["vip"]["days_left"]
    request_id = str(uuid.uuid4())
    body = {"item_id": by_code["vip_7d"]["id"], "request_id": request_id}
    first, second = await asyncio.gather(
        client.post(f"{API}/rewards/redemptions", json=body, headers=user.headers),
        client.post(f"{API}/rewards/redemptions", json=body, headers=user.headers),
    )
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["id"] == second.json()["id"] and first.json()["price_coins"] == 700
    wallet = await _wallet(client, user)
    assert wallet["coin_balance"] == 100 and wallet["vip"]["days_left"] == days_before + 7
    spent = (await client.get(f"{API}/rewards/wallet/ledger?currency=coin", headers=user.headers)).json()
    assert [e["amount"] for e in spent["items"]] == [-700, 800]
    assert spent["items"][0]["reason"] == "redemption"

    gone = await client.post(
        f"{API}/rewards/redemptions",
        json={"item_id": 999_999, "request_id": str(uuid.uuid4())},
        headers=user.headers,
    )
    assert (gone.status_code, error_code(gone)) == (404, "REWARD_ITEM_UNAVAILABLE")
    bad = await client.post(
        f"{API}/rewards/redemptions", json={"item_id": 1, "request_id": "x"}, headers=user.headers
    )
    assert bad.status_code == 422


async def test_frame_bought_in_shop_cannot_be_bought_twice_and_can_be_equipped(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-98 TC5, US-NH-99 TC1, TC2, TC5: mua khung rồi đeo; khung chưa có hoặc hết VIP thì từ chối."""
    admin, user = await make_admin(app, client), await register(client)
    await _adjust(client, admin, user, "coin", 1700)
    items = {
        i["code"]: i for i in (await client.get(f"{API}/rewards/shop/items", headers=user.headers)).json()
    }
    bamboo = items["frame_bamboo"]
    assert bamboo["frame"]["code"] == "bamboo_leaf" and bamboo["owned"] is False

    bought = await client.post(
        f"{API}/rewards/redemptions",
        json={"item_id": bamboo["id"], "request_id": str(uuid.uuid4())},
        headers=user.headers,
    )
    assert bought.status_code == 201
    twice = await client.post(
        f"{API}/rewards/redemptions",
        json={"item_id": bamboo["id"], "request_id": str(uuid.uuid4())},
        headers=user.headers,
    )
    assert (twice.status_code, error_code(twice)) == (409, "FRAME_ALREADY_OWNED")
    assert (await _wallet(client, user))["coin_balance"] == 900  # chỉ trừ một lần

    frames = {f["code"]: f for f in (await client.get(f"{API}/rewards/frames", headers=user.headers)).json()}
    assert set(frames) >= {"sakura_gold", "spring_petal", "vip_sakura", "bamboo_leaf", "ink_cloud"}
    assert frames["bamboo_leaf"]["owned"] and frames["bamboo_leaf"]["equippable"]
    assert frames["bamboo_leaf"]["acquire_label"] == "Đổi ở cửa hàng"
    assert frames["vip_sakura"]["equippable"] is True  # đang VIP (quà chào mừng)
    assert frames["ink_cloud"]["owned"] is False

    equip = await client.put(
        f"{API}/rewards/frames/equipped", json={"frame_code": "bamboo_leaf"}, headers=user.headers
    )
    assert equip.status_code == 200 and equip.json()["equipped_frame"]["code"] == "bamboo_leaf"
    assert (await _wallet(client, user))["equipped_frame"]["style_key"] == "bamboo_leaf"  # đúng sau F5

    for code in ("ink_cloud", "sakura_gold", "khong_co"):
        res = await client.put(
            f"{API}/rewards/frames/equipped", json={"frame_code": code}, headers=user.headers
        )
        assert (res.status_code, error_code(res)) == (409, "FRAME_NOT_AVAILABLE"), code
    assert (await _wallet(client, user))["equipped_frame"]["code"] == "bamboo_leaf"  # giữ nguyên

    await client.put(
        f"{API}/rewards/frames/equipped", json={"frame_code": "vip_sakura"}, headers=user.headers
    )
    assert (await _wallet(client, user))["equipped_frame"]["code"] == "vip_sakura"
    await _drop_vip(client, admin, user)
    assert (await _wallet(client, user))["equipped_frame"] is None  # khung VIP tự không hiện khi hết VIP
    refused = await client.put(
        f"{API}/rewards/frames/equipped", json={"frame_code": "vip_sakura"}, headers=user.headers
    )
    assert (refused.status_code, error_code(refused)) == (409, "FRAME_NOT_AVAILABLE")
    removed = await client.put(
        f"{API}/rewards/frames/equipped", json={"frame_code": None}, headers=user.headers
    )
    assert removed.status_code == 200 and removed.json()["equipped_frame"] is None


# ---- truyện VIP --------------------------------------------------------------------------------------------


async def _vip_series(client: httpx.AsyncClient, admin: Account) -> dict[str, Any]:
    """Truyện công khai có chương đọc thử và chương khóa, mỗi chương một trang; đã bật cờ VIP."""
    res = await client.post(
        f"{API}/series",
        json={"title_vi": f"Truyện VIP {uuid.uuid4().hex[:8]}", "visibility": "public"},
        headers=admin.headers,
    )
    assert res.status_code == 201, res.text
    series_id = res.json()["id"]
    out: dict[str, Any] = {"series_id": series_id}
    for name, number, trial in (("trial", 1, True), ("locked", 2, False)):
        chapter = await client.post(
            f"{API}/series/{series_id}/chapters",
            json={"number": number, "is_trial": trial},
            headers=admin.headers,
        )
        assert chapter.status_code == 201, chapter.text
        upload = await client.post(
            f"{API}/chapters/{chapter.json()['id']}/pages",
            files=[("files", ("p.png", _png(), "application/octet-stream"))],
            headers=admin.headers,
        )
        assert upload.status_code == 201, upload.text
        page = upload.json()["results"][0]["page"]
        out[name] = {
            "chapter_id": chapter.json()["id"],
            "page_id": page["id"],
            "file_url": page["original_url"],
        }
    flag = await client.put(
        f"{API}/admin/series/{series_id}/vip", json={"is_vip": True}, headers=admin.headers
    )
    assert flag.status_code == 200, flag.text
    return out


async def test_vip_series_blocks_chapter_page_bubbles_progress_and_file_urls_for_non_vip(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-96 TC1-TC6, F17.05, F03.10: chặn chương, trang, bong bóng, tiến độ và ảnh qua đường dẫn tệp."""
    admin = await make_admin(app, client)
    series = await _vip_series(client, admin)
    sid, trial, locked = series["series_id"], series["trial"], series["locked"]
    user = await _non_vip_user(client, admin)

    detail = (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()
    assert detail["series"]["is_vip"] is True and detail["series"]["vip_access"] == "trial_only"
    flags = {c["id"]: (c["is_trial"], c["is_locked"]) for c in detail["chapters"]}
    assert flags == {trial["chapter_id"]: (True, False), locked["chapter_id"]: (False, True)}
    listing = (await client.get(f"{API}/series?size=100", headers=user.headers)).json()["items"]
    assert next(s for s in listing if s["id"] == sid)["vip_access"] == "trial_only"

    assert (
        await client.get(f"{API}/chapters/{trial['chapter_id']}", headers=user.headers)
    ).status_code == 200
    denied = await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    assert (denied.status_code, error_code(denied)) == (403, "VIP_REQUIRED")
    assert denied.json()["error"]["details"] == {"series_id": sid, "has_tickets": False}
    for path in (f"/pages/{locked['page_id']}", f"/pages/{locked['page_id']}/reading"):
        res = await client.get(f"{API}{path}", headers=user.headers)
        assert (res.status_code, error_code(res)) == (403, "VIP_REQUIRED"), path
    progress = await client.put(
        f"{API}/chapters/{locked['chapter_id']}/progress", json={"page_no": 1}, headers=user.headers
    )
    assert (progress.status_code, error_code(progress)) == (403, "VIP_REQUIRED")

    # Ảnh trang: chương đọc thử mở, chương khóa trả 404 như không thấy tệp; Khách cũng không đọc được.
    assert (await client.get(trial["file_url"], headers=user.headers)).status_code == 200
    assert (await client.get(trial["file_url"])).status_code == 200
    assert (await client.get(locked["file_url"], headers=user.headers)).status_code == 404
    assert (await client.get(locked["file_url"])).status_code == 404

    guest = await client.get(f"{API}/chapters/{locked['chapter_id']}")
    assert (guest.status_code, error_code(guest)) == (401, "LOGIN_REQUIRED")

    # Có vé thì lời từ chối báo "còn vé" để giao diện gợi ý dùng vé.
    await _adjust(client, admin, user, "ticket", 1)
    hinted = await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    assert hinted.json()["error"]["details"]["has_tickets"] is True

    # Quản trị viên đọc mọi chương dù không VIP (TC6).
    assert (
        await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=admin.headers)
    ).status_code == 200
    assert (await client.get(locked["file_url"], headers=admin.headers)).status_code == 200
    admin_view = (await client.get(f"{API}/series/{sid}", headers=admin.headers)).json()
    assert admin_view["series"]["vip_access"] == "vip"
    assert [c["is_locked"] for c in admin_view["chapters"]] == [False, False]


async def test_vip_user_reads_all_until_vip_expires_then_is_blocked_again(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-96 TC3, TC4, US-NH-94 TC3: VIP đọc hết; hết VIP thì yêu cầu kế tiếp bị chặn, không cần job."""
    admin = await make_admin(app, client)
    series = await _vip_series(client, admin)
    sid, locked = series["series_id"], series["locked"]
    user = await register(client)  # còn 3 ngày VIP từ quà chào mừng

    assert (
        await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    ).status_code == 200
    assert (await client.get(locked["file_url"], headers=user.headers)).status_code == 200
    assert (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()["series"][
        "vip_access"
    ] == "vip"

    await _drop_vip(client, admin, user)  # VIP hết hạn giữa phiên
    blocked = await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    assert (blocked.status_code, error_code(blocked)) == (403, "VIP_REQUIRED")
    assert (await client.get(locked["file_url"], headers=user.headers)).status_code == 404

    # Hạn VIP quá khứ ghi trực tiếp (như hết hạn theo thời gian) cũng bị chặn ngay.
    await _grant_vip(client, admin, user, 1)
    async with app.state.container.session_factory() as session:
        await session.execute(
            text("UPDATE wallets SET vip_until = now() - interval '1 second' WHERE user_id = :u"),
            {"u": user.id},
        )
        await session.commit()
    again = await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    assert (again.status_code, error_code(again)) == (403, "VIP_REQUIRED")


async def test_ticket_unlock_is_permanent_idempotent_and_survives_vip_loss(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-97 TC1-TC6, F17.06."""
    admin = await make_admin(app, client)
    series = await _vip_series(client, admin)
    sid, locked = series["series_id"], series["locked"]
    user = await _non_vip_user(client, admin)

    no_ticket = await client.post(
        f"{API}/vip/unlocks", json={"series_id": sid, "request_id": str(uuid.uuid4())}, headers=user.headers
    )
    assert (no_ticket.status_code, error_code(no_ticket)) == (409, "NOT_ENOUGH_TICKETS")

    await _adjust(client, admin, user, "ticket", 2)
    request_id = str(uuid.uuid4())
    body = {"series_id": sid, "request_id": request_id}
    first = await client.post(f"{API}/vip/unlocks", json=body, headers=user.headers)
    replay = await client.post(f"{API}/vip/unlocks", json=body, headers=user.headers)
    assert (first.status_code, replay.status_code) == (201, 201)
    assert first.json()["tickets_left"] == 1 and replay.json()["tickets_left"] == 1
    assert (await _wallet(client, user))["ticket_balance"] == 1

    assert (
        await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    ).status_code == 200
    assert (await client.get(locked["file_url"], headers=user.headers)).status_code == 200
    assert (await client.get(f"{API}/series/{sid}", headers=user.headers)).json()["series"][
        "vip_access"
    ] == "unlocked"
    unlocks = (await client.get(f"{API}/vip/unlocks", headers=user.headers)).json()
    assert [u["series_id"] for u in unlocks] == [sid] and unlocks[0]["series_title"]
    assert (await client.get(f"{API}/vip/me", headers=user.headers)).json()["unlocked_series_count"] == 1

    again = await client.post(
        f"{API}/vip/unlocks", json={"series_id": sid, "request_id": str(uuid.uuid4())}, headers=user.headers
    )
    assert (again.status_code, error_code(again)) == (409, "SERIES_ALREADY_UNLOCKED")
    assert (await _wallet(client, user))["ticket_balance"] == 1

    # Đang VIP rồi hết VIP: truyện đã mở khóa bằng vé vẫn đọc được (TC5).
    await _grant_vip(client, admin, user, 5)
    await _drop_vip(client, admin, user)
    assert (
        await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=user.headers)
    ).status_code == 200

    # Truyện không còn cờ VIP thì ai cũng đọc như truyện thường; vé không hoàn (TC6).
    stranger = await _non_vip_user(client, admin)
    assert (
        await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=stranger.headers)
    ).status_code == 403
    unflag = await client.put(f"{API}/admin/series/{sid}/vip", json={"is_vip": False}, headers=admin.headers)
    assert unflag.status_code == 200
    assert (
        await client.get(f"{API}/chapters/{locked['chapter_id']}", headers=stranger.headers)
    ).status_code == 200
    assert (await client.get(locked["file_url"], headers=stranger.headers)).status_code == 200
    assert (await _wallet(client, user))["ticket_balance"] == 1
    plain = await client.post(
        f"{API}/vip/unlocks",
        json={"series_id": sid, "request_id": str(uuid.uuid4())},
        headers=stranger.headers,
    )
    assert (plain.status_code, error_code(plain)) == (409, "SERIES_NOT_VIP")
    missing = await client.post(
        f"{API}/vip/unlocks",
        json={"series_id": 999_999_999, "request_id": str(uuid.uuid4())},
        headers=user.headers,
    )
    assert (missing.status_code, error_code(missing)) == (404, "SERIES_NOT_FOUND")


async def test_admin_series_vip_flag_rules_and_reward_item_management(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-QT-17 TC1-TC6, F17.09."""
    admin, user = await make_admin(app, client), await register(client)

    private = await client.post(
        f"{API}/series", json={"title_vi": f"Riêng {uuid.uuid4().hex[:6]}"}, headers=user.headers
    )
    refused = await client.put(
        f"{API}/admin/series/{private.json()['id']}/vip", json={"is_vip": True}, headers=admin.headers
    )
    assert (refused.status_code, error_code(refused)) == (409, "SERIES_NOT_PUBLIC")
    nothing = await client.put(
        f"{API}/admin/series/999999999/vip", json={"is_vip": True}, headers=admin.headers
    )
    assert nothing.status_code == 404

    public = await client.post(
        f"{API}/series",
        json={"title_vi": f"Công khai {uuid.uuid4().hex[:6]}", "visibility": "public"},
        headers=admin.headers,
    )
    flagged = await client.put(
        f"{API}/admin/series/{public.json()['id']}/vip", json={"is_vip": True}, headers=admin.headers
    )
    assert flagged.json()["warning"] == "Truyện chưa có chương đọc thử" and flagged.json()["is_vip"] is True
    audit = (
        await client.get(f"{API}/admin/audit-logs?action=series.vip_changed&size=50", headers=admin.headers)
    ).json()
    assert any(a["target_id"] == public.json()["id"] for a in audit["items"])
    # Truyện VIP đổi sang riêng tư thì không còn là VIP (ràng buộc CSDL không bị vi phạm).
    await client.put(
        f"{API}/admin/series/{public.json()['id']}/vip", json={"is_vip": False}, headers=admin.headers
    )

    code = f"vip_{uuid.uuid4().hex[:8]}"
    created = await client.post(
        f"{API}/admin/reward-items",
        json={"code": code, "name": "3 ngày VIP", "kind": "vip_days", "price_coins": 360, "vip_days": 3},
        headers=admin.headers,
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    dup = await client.post(
        f"{API}/admin/reward-items",
        json={"code": code, "name": "trùng", "kind": "vip_days", "price_coins": 1, "vip_days": 1},
        headers=admin.headers,
    )
    assert (dup.status_code, error_code(dup)) == (409, "REWARD_ITEM_CODE_TAKEN")
    for payload in (
        {"code": "gia_cao", "name": "x", "kind": "vip_days", "price_coins": 100_001, "vip_days": 1},
        {"code": "gia_0", "name": "x", "kind": "vip_days", "price_coins": 0, "vip_days": 1},
        {"code": "thieu", "name": "x", "kind": "vip_days", "price_coins": 5},
        {
            "code": "khung_mua",
            "name": "x",
            "kind": "avatar_frame",
            "price_coins": 5,
            "frame_code": "sakura_gold",
        },
        {
            "code": "khung_vip",
            "name": "x",
            "kind": "avatar_frame",
            "price_coins": 5,
            "frame_code": "vip_sakura",
        },
    ):
        res = await client.post(f"{API}/admin/reward-items", json=payload, headers=admin.headers)
        assert res.status_code in (400, 422), payload

    shop = {
        i["code"]: i for i in (await client.get(f"{API}/rewards/shop/items", headers=user.headers)).json()
    }
    assert shop[code]["price_coins"] == 360

    await _adjust(client, admin, user, "coin", 400)
    redeem = await client.post(
        f"{API}/rewards/redemptions",
        json={"item_id": item_id, "request_id": str(uuid.uuid4())},
        headers=user.headers,
    )
    assert redeem.status_code == 201 and redeem.json()["price_coins"] == 360

    repriced = await client.patch(
        f"{API}/admin/reward-items/{item_id}",
        json={"price_coins": 500, "is_active": False},
        headers=admin.headers,
    )
    assert repriced.status_code == 200 and repriced.json()["has_redemptions"] is True
    locked = await client.patch(
        f"{API}/admin/reward-items/{item_id}", json={"vip_days": 9}, headers=admin.headers
    )
    assert (locked.status_code, error_code(locked)) == (409, "REWARD_ITEM_LOCKED")
    assert code not in {
        i["code"] for i in (await client.get(f"{API}/rewards/shop/items", headers=user.headers)).json()
    }
    listed = (await client.get(f"{API}/admin/reward-items", headers=admin.headers)).json()
    assert next(i for i in listed if i["code"] == code)["is_active"] is False
    ledger = (await client.get(f"{API}/rewards/wallet/ledger?currency=coin", headers=user.headers)).json()
    assert ledger["items"][0]["amount"] == -360  # lượt đổi cũ giữ giá lúc đổi
    actions = (await client.get(f"{API}/admin/audit-logs?size=100", headers=admin.headers)).json()["items"]
    assert {"reward_item.created", "reward_item.updated"} <= {a["action"] for a in actions}
    assert (
        await client.patch(f"{API}/admin/reward-items/999999999", json={"name": "x"}, headers=admin.headers)
    ).status_code == 404


async def test_patch_reward_item_clears_description_and_limit_with_null_and_keeps_missing_fields(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-QT-17 / F17.09: null tường minh xóa mô tả, giới hạn; trường vắng giữ nguyên."""
    admin = await make_admin(app, client)
    created = await client.post(
        f"{API}/admin/reward-items",
        json={
            "code": f"null_{uuid.uuid4().hex[:8]}",
            "name": "Món thử",
            "kind": "vip_days",
            "price_coins": 100,
            "vip_days": 1,
            "description": "mô tả cũ",
            "per_user_limit": 2,
        },
        headers=admin.headers,
    )
    assert created.status_code == 201, created.text
    url = f"{API}/admin/reward-items/{created.json()['id']}"
    kept = await client.patch(url, json={"price_coins": 120}, headers=admin.headers)
    assert (kept.json()["description"], kept.json()["per_user_limit"]) == ("mô tả cũ", 2)
    cleared = await client.patch(
        url, json={"description": None, "per_user_limit": None}, headers=admin.headers
    )
    assert cleared.status_code == 200, cleared.text
    assert (cleared.json()["description"], cleared.json()["per_user_limit"]) == (None, None)
    assert cleared.json()["price_coins"] == 120
    listed = (await client.get(f"{API}/admin/reward-items", headers=admin.headers)).json()
    stored = next(i for i in listed if i["id"] == created.json()["id"])
    assert (stored["description"], stored["per_user_limit"]) == (None, None)
    for field in ("name", "price_coins", "is_active", "sort_order"):
        res = await client.patch(url, json={field: None}, headers=admin.headers)
        assert res.status_code in (400, 422), field


async def test_admin_lists_all_avatar_frames_regardless_of_own_wallet(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """F17.09: GET /admin/avatar-frames trả mọi khung đang dùng cho form món; Người học bị 403, khách 401."""
    admin, user = await make_admin(app, client), await register(client)
    res = await client.get(f"{API}/admin/avatar-frames", headers=admin.headers)
    assert res.status_code == 200, res.text
    frames = {f["code"]: f for f in res.json()}
    assert {"sakura_gold", "vip_sakura"} <= set(frames)
    assert frames["vip_sakura"]["acquire_kind"] == "vip" and frames["vip_sakura"]["acquire_label"]
    assert {"id", "code", "name", "description", "style_key", "acquire_kind", "acquire_label"} == set(
        frames["vip_sakura"]
    )
    assert (await client.get(f"{API}/admin/avatar-frames", headers=user.headers)).status_code == 403
    assert (await client.get(f"{API}/admin/avatar-frames")).status_code == 401


# ---- hạn mức AI theo VIP (F17.04) ---------------------------------------------------------------------


async def test_ai_limits_follow_vip_and_admin_configuration(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-95 TC1-TC4: VIP 10/40/60/40, không VIP 5/20/30/20; đổi cấu hình có hiệu lực ngay."""
    admin = await make_admin(app, client)
    user = await register(client)
    vip_limits = (await client.get(f"{API}/vip/me", headers=user.headers)).json()["ai_limits"]
    assert vip_limits["quiz_daily_llm_limit"] == 10 and vip_limits["grammar_daily_limit"] == 60

    policies = app.state.container.ai_policies
    assert await policies.quiz.daily_limit(user.id) == 10
    assert await policies.ai_note.daily_limit(user.id) == 40
    assert await policies.grammar.daily_limit(user.id) == 60
    assert await policies.mistake_review.daily_limit(user.id) == 40

    await _drop_vip(client, admin, user)
    plain = (await client.get(f"{API}/vip/me", headers=user.headers)).json()["ai_limits"]
    assert plain == {
        "quiz_daily_llm_limit": 5,
        "ai_note_daily_limit": 20,
        "grammar_daily_limit": 30,
        "mistake_review_daily_limit": 20,
    }
    assert await policies.ai_note.daily_limit(user.id) == 20

    keys = ("vip_quiz_daily_llm_limit", "vip_ai_note_daily_limit")
    try:
        await _grant_vip(client, admin, user, 2)
        patch = await client.patch(
            f"{API}/admin/system-settings",
            json={"vip_quiz_daily_llm_limit": 3, "vip_ai_note_daily_limit": 100},
            headers=admin.headers,
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["values"]["vip_ai_note_daily_limit"] == 100
        assert await policies.quiz.daily_limit(user.id) == 5  # VIP thấp hơn thường: giữ hạn mức thường
        assert await policies.ai_note.daily_limit(user.id) == 100
    finally:
        await client.patch(f"{API}/admin/system-settings", json=dict.fromkeys(keys), headers=admin.headers)
    assert await policies.ai_note.daily_limit(user.id) == 40

    llm = await app.state.container.ai_policies.quiz.llm_enabled()
    assert llm is False  # test không bao giờ bật LLM thật; tắt LLM áp dụng cho cả VIP


# ---- nhắc VIP sắp hết hạn (US-HG-06) ---------------------------------------------------------------


async def test_vip_expiry_reminder_job_sends_once_per_expiry_and_skips_locked_accounts(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-HG-06 TC1-TC3: một thông báo cho mỗi hạn; hạn mới được nhắc lại; tài khoản bị khóa không nhận."""
    user, locked = await register(client), await register(client)
    container = app.state.container
    remind = RemindVipExpiryUseCase(
        lambda: SqlRewardsUnitOfWork(container.session_factory),
        build_reward_notifier(
            container.session_factory, container.settings.storage_dir / "outbox", container.clock
        ),
    )

    async def set_expiry(who: Account, interval: str) -> None:
        async with container.session_factory() as session:
            await session.execute(
                text(f"UPDATE wallets SET vip_until = now() + interval '{interval}' WHERE user_id = :u"),
                {"u": who.id},
            )
            await session.commit()

    async def expiring_count(who: Account) -> int:
        return (await _notification_kinds(client, who)).count("vip_expiring")

    await set_expiry(user, "10 hours")
    await set_expiry(locked, "10 hours")
    async with container.session_factory() as session:
        await session.execute(text("UPDATE users SET status = 'locked' WHERE id = :u"), {"u": locked.id})
        await session.commit()

    await remind.execute(datetime.now(timezone.utc))
    await remind.execute(datetime.now(timezone.utc))
    assert await expiring_count(user) == 1
    async with container.session_factory() as session:
        count = (
            await session.execute(
                text("SELECT count(*) FROM notifications WHERE user_id = :u AND kind = 'vip_expiring'"),
                {"u": locked.id},
            )
        ).scalar_one()
    assert count == 0

    await set_expiry(user, "12 hours")  # hạn đổi (như được cộng thêm) nên được nhắc lại
    await remind.execute(datetime.now(timezone.utc))
    assert await expiring_count(user) == 2
    await set_expiry(user, "3 days")
    await remind.execute(datetime.now(timezone.utc))
    assert await expiring_count(user) == 2  # còn xa: chưa nhắc


# ---- ghi sổ trên CSDL thật: khóa dòng ví, chống trùng, số dư không âm (F17.01) ------------------


async def test_concurrent_grants_with_same_key_credit_once_and_concurrent_spends_never_go_negative(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """F17.01, US-NH-93 TC4: khóa chống trùng chịu đồng thời; ba lượt đổi cùng lúc chỉ một lượt đủ xu."""
    from app.modules.rewards.application.public import (
        GrantCommand,
        GrantRewardUseCase,
        LedgerReason,
        RewardBundle,
    )

    user = await register(client)
    container = app.state.container
    grant = GrantRewardUseCase(lambda: SqlRewardsUnitOfWork(container.session_factory), container.clock)
    command = GrantCommand(
        user.id, RewardBundle(coins=150), "quests_all:2026-10-30", LedgerReason.QUEST_BONUS
    )
    results = await asyncio.gather(*(grant.execute(command) for _ in range(5)))
    assert sorted(r.duplicate for r in results) == [False, True, True, True, True]
    assert (await _wallet(client, user))["coin_balance"] == 150

    items = {
        i["code"]: i for i in (await client.get(f"{API}/rewards/shop/items", headers=user.headers)).json()
    }
    vip_1d = items["vip_1d"]["id"]  # 120 xu: số dư 150 chỉ đủ một lần
    attempts = await asyncio.gather(
        *(
            client.post(
                f"{API}/rewards/redemptions",
                json={"item_id": vip_1d, "request_id": str(uuid.uuid4())},
                headers=user.headers,
            )
            for _ in range(3)
        )
    )
    assert sorted(r.status_code for r in attempts) == [201, 409, 409]
    assert (await _wallet(client, user))["coin_balance"] == 30
