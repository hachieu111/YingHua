"""F09.09: script tính độ khó câu ví dụ Tatoeba — đúng cấp, chạy lại không đổi, --force tính lại."""

from __future__ import annotations

import importlib.util
import random
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import SERVER_DIR, Settings

pytestmark = pytest.mark.integration


def _load_script() -> object:
    path = SERVER_DIR / "scripts" / "compute_example_difficulty.py"
    spec = importlib.util.spec_from_file_location("compute_example_difficulty", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def test_script_computes_difficulty_once_and_force_recomputes(test_settings: Settings) -> None:
    script = _load_script()
    base = random.randrange(0x3400, 0x3400 + 3000)
    easy, hard = chr(base), chr(base + 1)
    engine = create_async_engine(test_settings.database_url)
    async with engine.begin() as conn:
        for word, level in ((easy, 1), (hard, 5)):
            await conn.execute(
                text(
                    "INSERT INTO hsk_words (word, level, list_version) VALUES (:w, :l, '3.0') "
                    "ON CONFLICT (word) DO UPDATE SET level = :l"
                ),
                {"w": word, "l": level},
            )
        entry_id = (
            await conn.execute(
                text(
                    "INSERT INTO dict_entries (simplified, pinyin, pinyin_numeric, pinyin_search, source) "
                    "VALUES (:w, 'x', 'x1', 'x', 'cvdict') "
                    "ON CONFLICT (simplified, pinyin_numeric, source) DO UPDATE SET pinyin = 'x' RETURNING id"
                ),
                {"w": easy},
            )
        ).scalar_one()
        ids = []
        for zh in (f"{easy}{easy}。", f"{easy}{hard}。"):
            row = await conn.execute(
                text(
                    "INSERT INTO dict_examples (entry_id, zh, source) "
                    "VALUES (:e, :zh, 'tatoeba') RETURNING id"
                ),
                {"e": entry_id, "zh": zh},
            )
            ids.append(row.scalar_one())

    async def levels() -> list[int | None]:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text("SELECT difficulty_level FROM dict_examples WHERE id = ANY(:ids) ORDER BY id"),
                {"ids": ids},
            )
            return [r[0] for r in rows]

    from sqlalchemy.ext.asyncio import AsyncSession

    try:
        async with AsyncSession(engine) as session:
            first = await script.compute(session, force=False)  # type: ignore[attr-defined]
        assert await levels() == [1, 5]
        assert first[1] >= 1 and first[5] >= 1
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE dict_examples SET difficulty_level = 9 WHERE id = ANY(:ids)"), {"ids": ids}
            )
        async with AsyncSession(engine) as session:
            await script.compute(session, force=False)  # type: ignore[attr-defined]
        assert await levels() == [9, 9]  # chạy lại không đụng dòng đã có độ khó
        async with AsyncSession(engine) as session:
            await script.compute(session, force=True)  # type: ignore[attr-defined]
        assert await levels() == [1, 5]
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM dict_examples WHERE id = ANY(:ids)"), {"ids": ids})
            await conn.execute(text("DELETE FROM dict_entries WHERE id = :e"), {"e": entry_id})
            await conn.execute(text("DELETE FROM hsk_words WHERE word = ANY(:w)"), {"w": [easy, hard]})
        await engine.dispose()
