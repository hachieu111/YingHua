"""Định dạng lỗi chuẩn và request_id (rules/api-conventions.md, error-handling.md, monitoring.md)."""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.core.errors import NotFoundError


class _Body(BaseModel):
    n: int


def _add_probe_routes(app: FastAPI) -> None:
    async def raise_not_found() -> None:
        raise NotFoundError("Không tìm thấy truyện", details={"series_id": 9})

    async def echo(body: _Body) -> _Body:
        return body

    async def crash() -> None:
        raise RuntimeError("bí mật nội bộ")

    app.add_api_route("/probe/not-found", raise_not_found)
    app.add_api_route("/probe/echo", echo, methods=["POST"])
    app.add_api_route("/probe/crash", crash)


async def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    )


async def test_domain_error_uses_standard_body(app: FastAPI) -> None:
    _add_probe_routes(app)
    async with await _client(app) as http:
        res = await http.get("/probe/not-found")
    assert res.status_code == 404
    assert res.json() == {
        "error": {"code": "NOT_FOUND", "message": "Không tìm thấy truyện", "details": {"series_id": 9}}
    }


async def test_validation_error_does_not_echo_input(app: FastAPI) -> None:
    _add_probe_routes(app)
    async with await _client(app) as http:
        res = await http.post("/probe/echo", json={"n": "khong-phai-so-bi-mat"})
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert "khong-phai-so-bi-mat" not in res.text
    assert body["details"]["fields"][0]["loc"] == ["body", "n"]


async def test_unknown_route_and_crash_use_standard_body(app: FastAPI) -> None:
    _add_probe_routes(app)
    async with await _client(app) as http:
        missing = await http.get("/khong-co")
        crash = await http.get("/probe/crash")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"
    assert crash.status_code == 500 and crash.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "bí mật nội bộ" not in crash.text


async def test_request_id_is_generated_or_echoed(app: FastAPI) -> None:
    _add_probe_routes(app)
    async with await _client(app) as http:
        generated = await http.get("/probe/not-found")
        echoed = await http.get("/probe/not-found", headers={"X-Request-ID": "abc-123"})
        rejected = await http.get("/probe/not-found", headers={"X-Request-ID": "<script>"})
    assert len(generated.headers["X-Request-ID"]) == 32
    assert echoed.headers["X-Request-ID"] == "abc-123"
    assert rejected.headers["X-Request-ID"] != "<script>"
