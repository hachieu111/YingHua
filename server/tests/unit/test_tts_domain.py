"""M11 — quy tắc thuần (F11.03, F11.04, F11.05) và SingleFlight."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.core.single_flight import SingleFlight
from app.modules.tts.domain.rules import (
    edge_rate,
    normalize_rate,
    normalize_text,
    split_into_chunks,
    text_digest,
)


def test_normalize_text_collapses_whitespace_and_digest_is_stable() -> None:
    assert normalize_text("  你好 \n 世界\t") == "你好 世界"
    assert text_digest(normalize_text(" 你好 ")) == text_digest("你好")
    assert len(text_digest("你好")) == 64


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, "1.00"), ("0.2", "0.50"), ("9", "1.50"), ("1.234", "1.23"), ("0.5", "0.50")],
)
def test_normalize_rate(raw: str | None, expected: str) -> None:
    assert normalize_rate(None if raw is None else Decimal(raw)) == Decimal(expected)


@pytest.mark.parametrize(("rate", "expected"), [("1.00", "+0%"), ("1.20", "+20%"), ("0.50", "-50%")])
def test_edge_rate_format(rate: str, expected: str) -> None:
    assert edge_rate(Decimal(rate)) == expected


def test_short_text_is_not_split() -> None:
    assert split_into_chunks("你好。") == ["你好。"]


def test_long_text_splits_on_sentence_boundaries_within_limit() -> None:
    text = "第一句话。" * 30
    chunks = split_into_chunks(text, 40)
    assert "".join(chunks) == text
    assert all(len(c) <= 40 for c in chunks)
    assert all(c.endswith("。") for c in chunks)


def test_sentence_longer_than_limit_is_cut_at_commas_then_hard() -> None:
    text = "甲乙丙，" * 10 + "丁" * 50
    chunks = split_into_chunks(text, 20)
    assert "".join(chunks) == text
    assert all(len(c) <= 20 for c in chunks)


async def test_single_flight_runs_once_and_shares_result_and_error() -> None:
    flight = SingleFlight()
    calls = 0

    async def work() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return 7

    assert await asyncio.gather(*(flight.run("k", work) for _ in range(4))) == [7] * 4
    assert calls == 1
    assert flight.pending == 0

    async def boom() -> int:
        await asyncio.sleep(0.01)
        raise ValueError("x")

    results = await asyncio.gather(flight.run("e", boom), flight.run("e", boom), return_exceptions=True)
    assert all(isinstance(r, ValueError) for r in results)
    assert flight.pending == 0
    assert await flight.run("e", work) == 7  # khóa đã được dọn, chạy lại được
