"""M07 — quy tắc thuần và bộ cắt ảnh ngữ cảnh: F07.01, F07.04, F07.07."""

from __future__ import annotations

import io
from decimal import Decimal

import pytest
from PIL import Image

from app.core.image_validation import CorruptImageError
from app.modules.vocab.domain.entities import CropBox
from app.modules.vocab.domain.errors import (
    InvalidHskFilterError,
    InvalidTermError,
    NoteTooLongError,
)
from app.modules.vocab.domain.rules import (
    SNIPPET_MAX_SIDE_PX,
    clean_note,
    contains_term,
    normalize_term,
    parse_hsk_filter,
    snippet_box,
    source_label,
)
from app.modules.vocab.infrastructure.snippet_cropper import PillowSnippetCropper


def test_normalize_term_requires_han_and_limits_length() -> None:
    assert normalize_term("  你好 ") == "你好"
    assert normalize_term("ＡＢ你") == "AB你"  # NFKC
    for bad in ("", "hello", "123", "你" * 33):
        with pytest.raises(InvalidTermError):
            normalize_term(bad)
    assert len(normalize_term("你" * 32)) == 32


def test_contains_term() -> None:
    assert contains_term("你好吗？", "你好") and not contains_term("你好", "再见")


def test_clean_note_trims_clears_and_limits() -> None:
    assert clean_note("  mẹo  ", 1000) == "mẹo"
    assert clean_note("   ", 1000) is None and clean_note(None, 1000) is None
    assert clean_note("a" * 1000, 1000) == "a" * 1000
    with pytest.raises(NoteTooLongError):
        clean_note("a" * 1001, 1000)


def test_parse_hsk_filter() -> None:
    assert parse_hsk_filter(None) == (None, False) and parse_hsk_filter("") == (None, False)
    assert parse_hsk_filter("3") == (3, False) and parse_hsk_filter("9") == (9, False)
    assert parse_hsk_filter("none") == (None, True) and parse_hsk_filter("NONE") == (None, True)
    for bad in ("0", "10", "abc", "-1", "1.5"):
        with pytest.raises(InvalidHskFilterError):
            parse_hsk_filter(bad)


def test_snippet_box_pads_clamps_and_rejects_empty() -> None:
    box = snippet_box(100, 100, 40, 20, 1000, 1000)
    assert box == CropBox(100 - 8, 100 - 8, 140 + 8, 120 + 8)
    assert snippet_box(0, 0, 40, 20, 1000, 1000) == CropBox(0, 0, 48, 28)  # kẹp vào mép ảnh
    assert snippet_box(990, 990, 40, 40, 1000, 1000) == CropBox(982, 982, 1000, 1000)
    assert snippet_box(5000, 5000, 40, 40, 1000, 1000) is None  # nằm ngoài ảnh
    assert snippet_box(10, 10, 0, 40, 1000, 1000) is None and snippet_box(10, 10, 5, 5, 0, 0) is None


def test_source_label() -> None:
    assert source_label("Hoa Hồng", Decimal("12.0"), 5) == "Hoa Hồng · Chương 12 · Trang 5"
    assert source_label("Hoa Hồng", Decimal("12.5"), 5) == "Hoa Hồng · Chương 12.5 · Trang 5"
    assert source_label("Hoa Hồng", Decimal("100"), 1) == "Hoa Hồng · Chương 100 · Trang 1"
    assert source_label(None, None, 2) == "Ảnh tải nhanh · Trang 2"
    assert len(source_label("A" * 400, Decimal(1), 1)) == 255


async def test_pillow_cropper_cuts_region_and_limits_size() -> None:
    """F07.01: ảnh ngữ cảnh là PNG hợp lệ, đúng vùng cắt, cạnh dài không vượt giới hạn."""
    buffer = io.BytesIO()
    image = Image.new("RGB", (2000, 3000), (255, 255, 255))
    image.paste((255, 0, 0), (100, 200, 300, 400))
    image.save(buffer, format="PNG")
    cropper = PillowSnippetCropper(max_bytes=10 * 1024 * 1024)

    small = await cropper.crop(buffer.getvalue(), CropBox(100, 200, 300, 400))
    assert small.info.mime_type == "image/png" and (small.info.width, small.info.height) == (200, 200)
    pixel = Image.open(io.BytesIO(small.data)).convert("RGB").getpixel((100, 100))
    assert pixel == (255, 0, 0)

    big = await cropper.crop(buffer.getvalue(), CropBox(0, 0, 2000, 3000))
    assert max(big.info.width, big.info.height) <= SNIPPET_MAX_SIDE_PX
    with pytest.raises(CorruptImageError):
        await cropper.crop(b"not an image", CropBox(0, 0, 10, 10))
