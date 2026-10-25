"""Giao diện React chạy ở cổng 3000 phải gọi được API; origin lạ thì không."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration

LOGIN = "/api/v1/auth/login"


async def _preflight(client: httpx.AsyncClient, origin: str) -> httpx.Response:
    return await client.options(
        LOGIN,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


async def test_frontend_origin_is_allowed(client: httpx.AsyncClient) -> None:
    res = await _preflight(client, "http://localhost:3000")
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_unknown_origin_is_not_allowed(client: httpx.AsyncClient) -> None:
    res = await _preflight(client, "https://evil.example.com")
    assert "access-control-allow-origin" not in res.headers
