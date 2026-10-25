"""M06 — đọc tệp nạp từ điển và danh sách HSK (F06.06, F06.07; US-QT-09, US-QT-10)."""

from __future__ import annotations

import json

import pytest

from app.modules.dictionary.domain.errors import DictionaryFileError
from app.modules.dictionary.infrastructure.parsers import parse_cvdict, parse_hsk


def _json(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def test_parse_cvdict_splits_meanings_by_slash() -> None:
    rows = parse_cvdict(
        _json({"学习": {"trad": "學習", "pinyin": "xue2 xi2", "definition": "học tập/ học hỏi/ "}})
    )
    assert len(rows) == 1
    row = rows[0]
    assert (row.simplified, row.traditional, row.source) == ("学习", "學習", "cvdict")
    assert row.pinyin == "xué xí" and row.pinyin_numeric == "xue2 xi2"
    assert [d.gloss for d in row.definitions] == ["học tập", "học hỏi"]


def test_parse_cvdict_drops_traditional_equal_to_simplified() -> None:
    rows = parse_cvdict(_json({"人": {"trad": "人", "pinyin": "ren2", "definition": "người"}}))
    assert rows[0].traditional is None


def test_parse_cvdict_skips_entries_without_han_or_data() -> None:
    rows = parse_cvdict(
        _json(
            {
                "abc": {"pinyin": "abc", "definition": "chữ Latin"},
                "人": {"pinyin": "", "definition": "thiếu pinyin"},
                "水": {"pinyin": "shui3", "definition": ""},
                "火": {"pinyin": "huo3", "definition": "lửa"},
            }
        )
    )
    assert [r.simplified for r in rows] == ["火"]


@pytest.mark.parametrize("data", [b"{khong phai json", b"[1, 2]", b"\xff\xfe\x00bad"])
def test_parse_cvdict_rejects_broken_file(data: bytes) -> None:
    with pytest.raises(DictionaryFileError):
        parse_cvdict(data)


def test_parse_cvdict_rejects_non_object_entry() -> None:
    with pytest.raises(DictionaryFileError):
        parse_cvdict(_json({"人": "người"}))


def _hsk_item(
    word: str, levels: list[str], pinyin: str = "x", pos: list[str] | None = None
) -> dict[str, object]:
    return {
        "simplified": word,
        "level": levels,
        "pos": pos or [],
        "forms": [{"transcriptions": {"pinyin": pinyin}}],
    }


def test_parse_hsk_json_uses_new_labels_and_merges_duplicates_to_lowest() -> None:
    rows, rejected = parse_hsk(
        _json(
            [
                _hsk_item("爱", ["new-2", "old-1"], "ài", ["v"]),
                _hsk_item("爱", ["new-4"], "ài", ["n"]),
                _hsk_item("旧词", ["old-3"]),
                _hsk_item("好", ["new-1", "new-3"]),
            ]
        )
    )
    by_word = {r.word: r for r in rows}
    assert by_word["爱"].level == 2 and by_word["爱"].pos == "v,n" and by_word["爱"].pinyin == "ài"
    assert by_word["好"].level == 1
    assert "旧词" not in by_word
    assert len(rejected) == 1 and "旧词" in rejected[0]


def test_parse_hsk_csv_with_header_and_bad_lines() -> None:
    data = "词,级\n学习,2,xuéxí\n坏行,abc\n\n单字\n龘,7\n".encode()
    rows, rejected = parse_hsk(data)
    assert [(r.word, r.level) for r in rows] == [("学习", 2), ("龘", 7)]
    assert rows[0].pinyin == "xuéxí"
    assert len(rejected) == 2


def test_parse_hsk_rejects_broken_file() -> None:
    with pytest.raises(DictionaryFileError):
        parse_hsk(b"\xff\xfe\x00bad")
    with pytest.raises(DictionaryFileError):
        parse_hsk(b"[ {broken")
    with pytest.raises(DictionaryFileError):
        parse_hsk(b"[1, 2]")
