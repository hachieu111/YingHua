from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
async def test_health_reports_database_ok(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


async def test_openapi_is_served_under_api_prefix(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/v1/openapi.json")
    assert res.status_code == 200
    assert "/api/v1/health" in res.json()["paths"]
