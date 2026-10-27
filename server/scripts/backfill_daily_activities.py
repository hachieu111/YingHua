"""Nạp bù bảng `daily_activities` từ dữ liệu cũ (F12.01, F12.02) — chạy một lần, chạy lại an toàn.

Tính lại từng bộ đếm từ `review_logs`, `page_reads`, `vocab_entries`, `quizzes` theo múi giờ
người học rồi ghi đè, nên chạy nhiều lần cho cùng kết quả
(idempotent). Chạy trong thư mục server/ sau `alembic upgrade head`:

    python scripts/backfill_daily_activities.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.container import build_container
from app.core.config import get_settings
from app.modules.stats.infrastructure.backfill import SqlActivityBackfill


async def main() -> None:
    container = build_container(get_settings())
    try:
        async with container.session_factory() as session:
            report = await SqlActivityBackfill(session).run()
            await session.commit()
        for name, rows in report.items():
            print(f"{name}: {rows} dòng (người, ngày)")
    finally:
        await container.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
