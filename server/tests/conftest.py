"""Fixture dùng chung. Test API chạy trên CSDL kiểm thử (TEST_DATABASE_URL), không bao giờ trên CSDL chính."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.main import create_app


class FixedClock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def now(self) -> datetime:
        return self.at


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc))


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    base = get_settings()
    if not base.test_database_url:
        pytest.skip("Chưa cấu hình TEST_DATABASE_URL")
    return base.model_copy(update={"env": "test", "database_url": base.test_database_url})


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    return create_app(test_settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    # ASGITransport không tự chạy lifespan nên mở lifespan bằng tay để container được tạo.
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
