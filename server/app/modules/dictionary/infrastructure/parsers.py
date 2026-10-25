"""Đọc tệp dữ liệu từ điển (F06.06) và danh sách HSK (F06.07) thành dòng dữ liệu domain."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

from app.modules.dictionary.domain.entities import Definition, EntryRow, HskRow
from app.modules.dictionary.domain.errors import DictionaryFileError
from app.modules.dictionary.domain.pinyin import has_han, numeric_to_marks

MAX_WORD_LENGTH = 64
_HSK3_TAG = re.compile(r"^new-([1-9])$")


def _load_json(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DictionaryFileError() from exc


def parse_cvdict(data: bytes) -> list[EntryRow]:
    """Định dạng CVDICT (JSON): {"学习": {"trad": "學習", "pinyin": "xue2 xi2", "definition": "học"}}"""
    payload = _load_json(data)
    if not isinstance(payload, dict):
        raise DictionaryFileError("Tệp CVDICT phải là một đối tượng JSON {từ: mục}")
    rows: list[EntryRow] = []
    for word, item in payload.items():
        if not isinstance(item, dict) or not isinstance(word, str):
            raise DictionaryFileError(f"Mục không hợp lệ: {word!r}")
        word = word.strip()
        numeric = str(item.get("pinyin") or "").strip()
        gloss = str(item.get("definition") or "").strip()
        if not word or len(word) > MAX_WORD_LENGTH or not has_han(word) or not numeric or not gloss:
            continue  # mục không phải từ tiếng Trung hoặc thiếu dữ liệu: bỏ qua
        senses = tuple(Definition("cvdict", s.strip()) for s in gloss.split("/") if s.strip())
        traditional = str(item.get("trad") or "").strip() or None
        rows.append(
            EntryRow(
                simplified=word,
                traditional=traditional if traditional != word else None,
                pinyin=numeric_to_marks(numeric),
                pinyin_numeric=numeric,
                han_viet=None,
                definitions=senses,
                english=(),
                part_of_speech=None,
                source="cvdict",
            )
        )
    return rows


def _parse_hsk_json(payload: Any) -> tuple[list[HskRow], list[str]]:
    """Định dạng complete-hsk-vocabulary: `level` dạng ["new-3", "old-4"]; dùng nhãn HSK 3.0 (new-N)."""
    if not isinstance(payload, list):
        raise DictionaryFileError("Tệp HSK JSON phải là một danh sách")
    merged: dict[str, tuple[int, str | None, list[str]]] = {}
    rejected: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            raise DictionaryFileError()
        word = str(item.get("simplified") or "").strip()
        levels = [int(m.group(1)) for tag in item.get("level", []) if (m := _HSK3_TAG.match(str(tag)))]
        if not word or not levels:
            rejected.append(f"{word or '(trống)'}: không có cấp HSK 3.0")
            continue
        forms = item.get("forms") or [{}]
        pinyin = (forms[0].get("transcriptions") or {}).get("pinyin") if isinstance(forms[0], dict) else None
        pos = [str(p) for p in item.get("pos", [])]
        if word in merged:  # từ nhiều cách đọc xuất hiện nhiều lần: lấy cấp thấp nhất, gộp từ loại
            old_level, old_pinyin, old_pos = merged[word]
            merged[word] = (
                min(old_level, min(levels)),
                old_pinyin,
                old_pos + [p for p in pos if p not in old_pos],
            )
        else:
            merged[word] = (min(levels), pinyin, pos)
    rows = [
        HskRow(word=w, level=lv, pinyin=py, pos=",".join(ps)[:64] or None)
        for w, (lv, py, ps) in merged.items()
    ]
    return rows, rejected


def _parse_hsk_csv(text: str) -> tuple[list[HskRow], list[str]]:
    """CSV đơn giản: `từ,cấp[,pinyin]` (dòng tiêu đề tùy chọn)."""
    rows: list[HskRow] = []
    rejected: list[str] = []
    for number, record in enumerate(csv.reader(io.StringIO(text)), start=1):
        if not record or not any(cell.strip() for cell in record):
            continue
        word = record[0].strip()
        if number == 1 and not (len(record) > 1 and record[1].strip().isdigit()):
            continue  # dòng tiêu đề: cột cấp không phải số (tiêu đề cũng có thể là chữ Hán, vd. "词,级")
        try:
            level = int(record[1].strip())
        except (IndexError, ValueError):
            rejected.append(f"dòng {number}: thiếu hoặc sai cấp HSK")
            continue
        pinyin = record[2].strip() if len(record) > 2 and record[2].strip() else None
        rows.append(HskRow(word=word, level=level, pinyin=pinyin, pos=None))
    return rows, rejected


def parse_hsk(data: bytes) -> tuple[list[HskRow], list[str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DictionaryFileError() from exc
    if text.lstrip().startswith("["):
        return _parse_hsk_json(_load_json(data))
    return _parse_hsk_csv(text)
