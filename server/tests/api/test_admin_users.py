"""M13 Quản trị người dùng — F13.01…F13.03, F13.06 (US-QT-01, US-QT-02, US-QT-03)."""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.helpers import error_code, make_admin, register

pytestmark = pytest.mark.integration


async def _audit_actions(app: FastAPI, target_id: int) -> list[str]:
    async with app.state.container.session_factory() as session:
        rows = await session.execute(
            text("SELECT action FROM admin_audit_logs WHERE target_id = :t ORDER BY id"), {"t": target_id}
        )
        return [r[0] for r in rows]


async def test_learner_cannot_use_admin_endpoints(client: httpx.AsyncClient) -> None:
    learner = await register(client)
    res = await client.get("/api/v1/admin/users", headers=learner.headers)
    assert res.status_code == 403 and error_code(res) == "PERMISSION_DENIED"
    assert (await client.get("/api/v1/admin/users")).status_code == 401


async def test_admin_lists_and_searches_users_by_email(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await make_admin(app, client)
    marker = f"tim.thay.toi.{uuid.uuid4().hex[:10]}"
    target = await register(client, email=f"{marker}@example.com")
    res = await client.get("/api/v1/admin/users", params={"q": marker}, headers=admin.headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1 and body["items"][0]["id"] == target.id
    assert "password" not in res.text and "hash" not in res.text
    none = await client.get(
        "/api/v1/admin/users", params={"q": "khong-co-ai-ten-nay-xyz"}, headers=admin.headers
    )
    assert none.json()["items"] == [] and none.json()["total"] == 0


async def test_search_treats_like_wildcards_literally(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await make_admin(app, client)
    res = await client.get("/api/v1/admin/users", params={"q": "%"}, headers=admin.headers)
    assert res.json()["total"] == 0


async def test_admin_changes_role_and_it_takes_effect_with_audit(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    admin = await make_admin(app, client)
    target = await register(client)
    res = await client.patch(
        f"/api/v1/admin/users/{target.id}/role", json={"role": "admin"}, headers=admin.headers
    )
    assert res.status_code == 200 and res.json()["role"] == "admin"
    assert (await client.get("/api/v1/admin/users", headers=target.headers)).status_code == 200
    assert await _audit_actions(app, target.id) == ["user.role_changed"]


async def test_admin_cannot_demote_self(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await make_admin(app, client)
    res = await client.patch(
        f"/api/v1/admin/users/{admin.id}/role", json={"role": "user"}, headers=admin.headers
    )
    assert res.status_code == 400
    assert res.json()["error"]["message"] == "Không thể tự hạ quyền chính mình"


async def test_role_change_of_unknown_user_is_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await make_admin(app, client)
    res = await client.patch(
        "/api/v1/admin/users/999999999/role", json={"role": "admin"}, headers=admin.headers
    )
    assert res.status_code == 404


async def test_lock_revokes_sessions_then_unlock_restores_access(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    admin = await make_admin(app, client)
    victim = await register(client)
    locked = await client.post(
        f"/api/v1/admin/users/{victim.id}/lock", json={"reason": "Spam"}, headers=admin.headers
    )
    assert locked.status_code == 200
    assert locked.json()["status"] == "locked" and locked.json()["locked_reason"] == "Spam"
    assert (await client.get("/api/v1/account/me", headers=victim.headers)).status_code == 401

    unlocked = await client.post(f"/api/v1/admin/users/{victim.id}/unlock", headers=admin.headers)
    assert unlocked.json()["status"] == "active" and unlocked.json()["locked_reason"] is None
    login = await client.post("/api/v1/auth/login", json={"email": victim.email, "password": victim.password})
    assert login.status_code == 200
    assert await _audit_actions(app, victim.id) == ["user.locked", "user.unlocked"]


async def test_admin_cannot_lock_self(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await make_admin(app, client)
    res = await client.post(f"/api/v1/admin/users/{admin.id}/lock", json={}, headers=admin.headers)
    assert res.status_code == 400
    assert res.json()["error"]["message"] == "Không thể tự khóa chính mình"
