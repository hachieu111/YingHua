"""Fixture dùng chung. Test API chạy trên CSDL kiểm thử (TEST_DATABASE_URL), không bao giờ trên CSDL chính."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import SERVER_DIR, Settings, get_settings
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
    if not (base.test_database_url.rsplit("/", 1)[-1]).endswith("_test"):
        pytest.fail("TEST_DATABASE_URL phải trỏ tới CSDL có tên kết thúc bằng _test")
    # Đưa CSDL kiểm thử lên migration mới nhất trước khi chạy test.
    env = {**os.environ, "ALEMBIC_TARGET": "test", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=SERVER_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade lỗi:\n{result.stderr}")
    # Test không bao giờ gọi LLM thật dù .env của máy dev đã bật (testing.md: dịch vụ ngoài luôn mock).
    overrides = {
        "env": "test",
        "database_url": base.test_database_url,
        "llm_enabled": False,
        "llm_api_key": None,
    }
    return base.model_copy(update=overrides)


@pytest.fixture
def outbox_dir(tmp_path: Path) -> Path:
    return tmp_path / "outbox"


@pytest.fixture
def app(test_settings: Settings, tmp_path: Path) -> FastAPI:
    # Email giả ghi vào thư mục tạm của từng test.
    return create_app(test_settings.model_copy(update={"storage_dir": tmp_path}))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    # ASGITransport không tự chạy lifespan nên mở lifespan bằng tay để container được tạo.
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
