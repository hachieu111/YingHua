"""M06 — pinyin, phân loại từ khóa tìm kiếm (F06.01, F06.02; US-NH-26, US-NH-27)."""

from __future__ import annotations

import pytest

from app.modules.dictionary.domain.pinyin import (
    QueryKind,
    classify_query,
    has_han,
    is_han_char,
    numeric_to_marks,
    search_key,
)


@pytest.mark.parametrize(
    ("numeric", "marked"),
    [
        ("xue2 xi2", "xué xí"),
        ("lv4", "lǜ"),
        ("nu:3", "nǚ"),
        ("lu:e4", "lüè"),
        ("ma5", "ma"),
        ("ma", "ma"),
        ("hui4", "huì"),
        ("liu2", "liú"),
        ("gou3", "gǒu"),
        ("Zhong1 guo2", "Zhōng guó"),
        ("A1", "Ā"),
        ("er2 hua4 yin1", "ér huà yīn"),
    ],
)
def test_numeric_to_marks_places_tone_on_correct_vowel(numeric: str, marked: str) -> None:
    assert numeric_to_marks(numeric) == marked


@pytest.mark.parametrize("token", ["5", ",", "123", "x5y"])
def test_numeric_to_marks_keeps_non_pinyin_tokens(token: str) -> None:
    assert numeric_to_marks(token) == token


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("xué xí", "xuexi"),
        ("xue2 xi2", "xuexi"),
        ("XUE2XI2", "xuexi"),
        ("nǚ", "nu"),
        ("nu:3", "nu"),
        ("lv4", "lu"),
        ("xi'an", "xian"),
    ],
)
def test_search_key_ignores_tones_case_and_spaces(text: str, key: str) -> None:
    assert search_key(text) == key


@pytest.mark.parametrize(
    ("query", "kind"),
    [
        ("学习", QueryKind.HAN),
        ("study 学", QueryKind.HAN),
        ("xue2xi2", QueryKind.PINYIN),
        ("xue2 xi2", QueryKind.PINYIN),
        ("nǚ", QueryKind.PINYIN),
        ("māma", QueryKind.PINYIN),
        ("mơ", QueryKind.VIETNAMESE),
        ("tư duy", QueryKind.VIETNAMESE),
        ("đi", QueryKind.VIETNAMESE),
        ("học tập", QueryKind.VIETNAMESE),
        ("xuexi", QueryKind.LATIN),
        ("hello", QueryKind.LATIN),
    ],
)
def test_classify_query(query: str, kind: QueryKind) -> None:
    assert classify_query(query) is kind


def test_is_han_char_and_has_han() -> None:
    assert is_han_char("学") and is_han_char("㐀")
    assert not is_han_char("a") and not is_han_char("1") and not is_han_char("，")
    assert has_han("abc学") and not has_han("abc 123 ，")
