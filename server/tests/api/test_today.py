"""F12.04 / US-NH-80 — GET /stats/today và bản quản trị chỉ đọc (F13.07)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from tests.api.test_gd6_a1 import _save_and_grade
from tests.helpers import make_admin, register

pytestmark = pytest.mark.integration

API = "/api/v1"


async def test_today_new_learner_guest_and_active_learner(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-80 TC1, TC4, TC5, TC8: khách 401, người mới, người học có thẻ và mục tiêu."""
    assert (await client.get(f"{API}/stats/today")).status_code == 401
    fresh = await register(client)
    new = (await client.get(f"{API}/stats/today", headers=fresh.headers)).json()
    assert [i["kind"] for i in new["items"]] == ["get_started"] and new["items"][0]["action"][
        "type"
    ] == "library"

    owner = await register(client)
    page, _, _ = await _save_and_grade(client, app, owner)
    chapter_id = (await client.get(f"{API}/pages/{page['id']}", headers=owner.headers)).json()["chapter_id"]
    await client.put(f"{API}/chapters/{chapter_id}/progress", json={"page_no": 1}, headers=owner.headers)
    await client.patch(f"{API}/settings", json={"weekly_page_goal": 50}, headers=owner.headers)

    plan = (await client.get(f"{API}/stats/today", headers=owner.headers)).json()
    kinds = [i["kind"] for i in plan["items"]]
    # Truyện thử chỉ có một trang đã đọc hết nên không còn "đọc dở": không có việc đọc tiếp.
    assert "weekly_goal" in kinds and "continue_reading" not in kinds
    order = ["review_due", "continue_reading", "take_quiz", "weekly_goal", "chapter_suggestions"]
    assert kinds == sorted(kinds, key=order.index)
    assert [i["priority"] for i in plan["items"]] == list(range(1, len(kinds) + 1))
    goal = next(i for i in plan["items"] if i["kind"] == "weekly_goal")
    assert goal["count"] == 49 and "49 trang" in goal["message"]
    assert goal["action"]["type"] == "library"
    assert plan["all_done"] is False

    admin = await make_admin(app, client)
    view = await client.get(f"{API}/admin/users/{owner.id}/stats/today", headers=admin.headers)
    assert view.status_code == 200 and [i["kind"] for i in view.json()["items"]] == kinds
    denied = await client.get(f"{API}/admin/users/{owner.id}/stats/today", headers=fresh.headers)
    assert denied.status_code == 403
