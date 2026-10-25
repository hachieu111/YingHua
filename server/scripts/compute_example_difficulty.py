"""Tính độ khó (cấp HSK) cho câu ví dụ Tatoeba trong `dict_examples.difficulty_level` (F09.09).

Độ khó của câu = cấp HSK cao nhất của các từ chữ Hán sau khi tách bằng jieba; từ ngoài HSK lấy cấp cao nhất
của các chữ cấu thành, không có nữa thì 7. Chạy được nhiều lần: mặc định chỉ tính các dòng còn NULL.

Chạy trong thư mục server/:
    python scripts/compute_example_difficulty.py                 # yinghua_db, chỉ dòng NULL
    python scripts/compute_example_difficulty.py --force         # tính lại tất cả
    python scripts/compute_example_difficulty.py --target test   # yinghua_test
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jieba
from sqlalchemy import bindparam, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import build_container
from app.core.config import get_settings
from app.modules.dictionary.domain.difficulty import example_difficulty
from app.modules.dictionary.infrastructure.orm_models import DictExampleModel, HskWordModel

BATCH = 2000
TATOEBA = "tatoeba"


def log(message: str) -> None:
    print(message, flush=True)


async def compute(session: AsyncSession, force: bool) -> collections.Counter[int | None]:
    """Tính theo lô (khóa theo id tăng dần) và trả phân bố độ khó của các dòng đã xử lý."""
    jieba.setLogLevel(60)
    levels = {w: lv for w, lv in (await session.execute(select(HskWordModel.word, HskWordModel.level))).all()}
    distribution: collections.Counter[int | None] = collections.Counter()
    last_id = 0
    while True:
        stmt = (
            select(DictExampleModel.id, DictExampleModel.zh)
            .where(DictExampleModel.source == TATOEBA, DictExampleModel.id > last_id)
            .order_by(DictExampleModel.id)
            .limit(BATCH)
        )
        if not force:
            stmt = stmt.where(DictExampleModel.difficulty_level.is_(None))
        rows = (await session.execute(stmt)).all()
        if not rows:
            return distribution
        values = []
        for example_id, zh in rows:
            level = example_difficulty(jieba.lcut(zh), levels)
            distribution[level] += 1
            values.append({"b_id": example_id, "b_level": level})
        table = DictExampleModel.__table__
        await session.execute(
            update(table)
            .where(table.c.id == bindparam("b_id"))
            .values(difficulty_level=bindparam("b_level")),
            values,
        )
        await session.commit()
        last_id = rows[-1][0]
        log(f"  đã tính đến id {last_id} ({sum(distribution.values())} câu)")


async def main(target: str, force: bool) -> None:
    settings = get_settings()
    url = settings.test_database_url if target == "test" else settings.database_url
    if url is None:
        raise SystemExit("Chưa cấu hình TEST_DATABASE_URL")
    container = build_container(settings.model_copy(update={"database_url": url}))
    try:
        async with container.session_factory() as session:
            distribution = await compute(session, force)
            total = (
                await session.execute(
                    select(func.count())
                    .select_from(DictExampleModel)
                    .where(DictExampleModel.source == TATOEBA)
                )
            ).scalar_one()
        log(f"Đã tính {sum(distribution.values())} / {total} câu Tatoeba. Phân bố theo cấp:")
        for level in sorted(distribution, key=lambda lv: (lv is None, lv or 0)):
            log(f"  cấp {level if level is not None else 'không có chữ Hán'}: {distribution[level]}")
    finally:
        await container.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tính độ khó câu ví dụ Tatoeba")
    parser.add_argument("--target", choices=("main", "test"), default="main")
    parser.add_argument("--force", action="store_true", help="Tính lại cả dòng đã có độ khó")
    args = parser.parse_args()
    asyncio.run(main(args.target, args.force))
