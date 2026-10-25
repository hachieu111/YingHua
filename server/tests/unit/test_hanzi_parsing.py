"""F06.05: kiểm cấu trúc dữ liệu nét viết, dữ liệu hỏng không được làm hỏng API."""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.dictionary.infrastructure.hanzi_parsing import (
    MAX_STROKES,
    parse_etymology,
    parse_stroke_data,
)

GOOD = {"strokes": ["M 1 1 Z", "M 2 2 Z"], "medians": [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]}


def test_valid_stroke_data_is_parsed() -> None:
    data = parse_stroke_data(GOOD)
    assert data is not None
    assert len(data.strokes) == len(data.medians) == 2
    assert data.medians[1] == ((5, 6), (7, 8))


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "x",
        {},
        {"strokes": "abc", "medians": []},
        {"strokes": [1], "medians": [[[1, 2]]]},
        {"strokes": ["a", "b"], "medians": [[[1, 2]]]},
        {"strokes": ["a"], "medians": [[[1, "2"]]]},
        {"strokes": ["a"], "medians": [[[1, 2, 3]]]},
        {"strokes": ["a"], "medians": [[]]},
        {"strokes": [], "medians": []},
    ],
)
def test_broken_stroke_data_returns_none(raw: Any) -> None:
    assert parse_stroke_data(raw) is None


def test_too_many_strokes_returns_none() -> None:
    n = MAX_STROKES + 1
    assert parse_stroke_data({"strokes": ["M 1 1 Z"] * n, "medians": [[[1, 2]]] * n}) is None


def test_etymology_keeps_only_text_fields() -> None:
    info = parse_etymology({"type": "ideographic", "hint": "woman", "phonetic": 5})
    assert info is not None and info.type == "ideographic" and info.phonetic is None


@pytest.mark.parametrize("raw", [None, [], {}, {"type": 1}])
def test_empty_etymology_returns_none(raw: Any) -> None:
    assert parse_etymology(raw) is None
