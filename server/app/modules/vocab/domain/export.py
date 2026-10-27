"""Dựng tệp xuất sổ tay (F07.08) — thuần Python, chỉ dùng thư viện chuẩn.

Chỉ xuất chữ Hán, pinyin, nghĩa, cấp HSK, trạng thái, ghi chú: không xuất ảnh ngữ cảnh hay dữ liệu
riêng tư khác.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.core.errors import InvalidInputError, NotFoundError
from app.modules.vocab.domain.entities import VocabEntry, VocabStatus

# Một lần xuất tối đa chừng này từ để tệp và thời gian xử lý không phình vô hạn; vượt thì yêu cầu lọc bớt.
MAX_EXPORT_ROWS = 5000
EXPORT_PAGE_SIZE = 500
UTF8_BOM = "﻿"
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

CSV_HEADER = ("Chữ Hán", "Pinyin", "Nghĩa", "Cấp HSK", "Trạng thái", "Ghi chú")
ANKI_DIRECTIVES = ("#separator:tab", "#html:false", "#tags column:3")
_STATUS_LABELS = {
    VocabStatus.LEARNING: "Đang học",
    VocabStatus.KNOWN: "Đã thuộc",
    VocabStatus.IGNORED: "Bỏ qua",
}
_STATUS_TAGS = {
    VocabStatus.LEARNING: "dang_hoc",
    VocabStatus.KNOWN: "da_thuoc",
    VocabStatus.IGNORED: "bo_qua",
}


class ExportFormat(str, Enum):
    CSV = "csv"
    ANKI = "anki"


class InvalidExportFormatError(InvalidInputError):
    code = "INVALID_EXPORT_FORMAT"
    default_message = "Định dạng xuất phải là csv hoặc anki"


class EmptyExportError(NotFoundError):
    code = "VOCAB_EXPORT_EMPTY"
    default_message = "Sổ tay chưa có từ để xuất"


class ExportTooLargeError(InvalidInputError):
    code = "VOCAB_EXPORT_TOO_LARGE"
    default_message = f"Có quá nhiều từ để xuất một lần (tối đa {MAX_EXPORT_ROWS}), hãy lọc bớt"


@dataclass(frozen=True, slots=True)
class ExportFile:
    filename: str
    media_type: str
    content: bytes
    row_count: int


def parse_export_format(value: str) -> ExportFormat:
    try:
        return ExportFormat(value)
    except ValueError as exc:
        raise InvalidExportFormatError() from exc


def export_filename(fmt: ExportFormat, today: date) -> str:
    """Tên tệp do hệ thống đặt (không lấy từ dữ liệu người dùng): chỉ ký tự an toàn."""
    stem = f"yinghua-sotay-{today:%Y%m%d}"
    return f"{stem}.csv" if fmt is ExportFormat.CSV else f"{stem}-anki.txt"


def _hsk_label(entry: VocabEntry) -> str:
    return f"HSK {entry.hsk_level}" if entry.hsk_level else "Ngoài HSK"


def _safe_cell(value: str | None) -> str:
    """Chống chèn công thức khi mở bằng bảng tính: ô bắt đầu bằng = + - @ được thêm dấu nháy đơn."""
    text = value or ""
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def render_csv(entries: Sequence[VocabEntry]) -> bytes:
    """CSV UTF-8 có BOM (Excel đọc đúng tiếng Việt và chữ Hán), xuống dòng CRLF theo RFC 4180."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for e in entries:
        writer.writerow(
            [
                _safe_cell(e.term),
                _safe_cell(e.pinyin),
                _safe_cell(e.meaning_vi),
                _hsk_label(e),
                _STATUS_LABELS[e.status],
                _safe_cell(e.note),
            ]
        )
    return (UTF8_BOM + buffer.getvalue()).encode("utf-8")


def _one_line(value: str | None) -> str:
    return " ".join((value or "").split())


def render_anki(entries: Sequence[VocabEntry]) -> bytes:
    """Tệp văn bản ngăn bằng tab nhập được vào Anki (Tệp > Nhập): Front = chữ Hán, Back = pinyin và nghĩa
    (như thẻ nhận diện), Tags = YingHua, cấp HSK, trạng thái. Ba dòng `#` đầu khai báo định dạng cho Anki."""
    lines = list(ANKI_DIRECTIVES)
    for e in entries:
        back = " — ".join(part for part in (_one_line(e.pinyin), _one_line(e.meaning_vi)) if part)
        hsk_tag = f"HSK{e.hsk_level}" if e.hsk_level else "HSK_ngoai"
        lines.append("\t".join([_one_line(e.term), back, f"YingHua {hsk_tag} {_STATUS_TAGS[e.status]}"]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_export(fmt: ExportFormat, entries: Sequence[VocabEntry], today: date) -> ExportFile:
    if not entries:
        raise EmptyExportError()
    if fmt is ExportFormat.CSV:
        return ExportFile(
            export_filename(fmt, today), "text/csv; charset=utf-8", render_csv(entries), len(entries)
        )
    return ExportFile(
        export_filename(fmt, today), "text/plain; charset=utf-8", render_anki(entries), len(entries)
    )
