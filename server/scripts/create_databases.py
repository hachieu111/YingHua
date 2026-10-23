"""Tạo CSDL chính và CSDL kiểm thử nếu chưa có (đọc DATABASE_URL, TEST_DATABASE_URL từ server/.env).

Chạy trong thư mục server/:  python scripts/create_databases.py
Chỉ tạo mới, không bao giờ xóa CSDL.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


async def ensure_database(url: str) -> None:
    target = make_url(url)
    name = target.database
    if not name or not name.replace("_", "").isalnum():
        raise SystemExit(f"Tên CSDL không hợp lệ: {name!r}")
    conn = await asyncpg.connect(
        user=target.username,
        password=target.password,
        host=target.host,
        port=target.port or 5432,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
        if exists:
            print(f"Đã có CSDL {name}")
            return
        # CREATE DATABASE không nhận tham số bind; tên đã được kiểm tra chỉ gồm chữ, số, '_'.
        await conn.execute(f"CREATE DATABASE \"{name}\" ENCODING 'UTF8' TEMPLATE template0")
        print(f"Đã tạo CSDL {name}")
    finally:
        await conn.close()


async def main() -> None:
    settings = get_settings()
    await ensure_database(settings.database_url)
    if settings.test_database_url:
        await ensure_database(settings.test_database_url)


if __name__ == "__main__":
    asyncio.run(main())
