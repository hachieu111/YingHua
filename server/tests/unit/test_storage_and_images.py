"""Kho tệp và kiểm tra ảnh tải lên (F03.07, F01.10, security.md: upload)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import NotFoundError
from app.core.image_validation import (
    CorruptImageError,
    ImageTooLargeError,
    UnsupportedImageError,
    inspect_image,
    sniff_mime,
)
from app.core.storage import LocalFileStorage, StagedFiles, StorageError
from tests.helpers import png_bytes

MB = 1024 * 1024


def test_inspect_real_png_returns_size_hash_and_extension() -> None:
    info = inspect_image(png_bytes(size=(30, 50)), "trang.PNG", 10 * MB)
    assert (info.mime_type, info.extension, info.width, info.height) == ("image/png", "png", 30, 50)
    assert len(info.sha256) == 64


def test_content_decides_not_extension() -> None:
    with pytest.raises(UnsupportedImageError):
        inspect_image(b"hello, not an image at all", "a.png", 10 * MB)
    with pytest.raises(UnsupportedImageError):
        inspect_image(png_bytes(), "a.gif", 10 * MB)
    with pytest.raises(UnsupportedImageError):
        inspect_image(png_bytes(), None, 10 * MB)


def test_truncated_image_is_rejected_as_corrupt() -> None:
    with pytest.raises(CorruptImageError):
        inspect_image(png_bytes()[:40], "a.png", 10 * MB)


def test_oversized_file_is_rejected_before_parsing() -> None:
    with pytest.raises(ImageTooLargeError):
        inspect_image(b"\x89PNG\r\n\x1a\n" + b"0" * (MB + 1), "a.png", MB)


def test_sniff_mime_recognises_jpeg_png_webp() -> None:
    assert sniff_mime(b"\xff\xd8\xff\xe0abc") == "image/jpeg"
    assert sniff_mime(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_mime(b"GIF89a") is None


async def test_storage_saves_with_random_relative_key_and_blocks_traversal(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path / "files")
    key = await storage.save(b"data", "original", "png")
    assert key.startswith("original/") and key.endswith(".png") and not Path(key).is_absolute()
    assert await storage.read(key) == b"data"
    await storage.delete(key)
    await storage.delete(key)  # xóa lặp không lỗi
    with pytest.raises(NotFoundError):
        await storage.read(key)
    with pytest.raises(StorageError):
        await storage.read("../../etc/passwd")
    with pytest.raises(StorageError):
        await storage.save(b"x", "../evil", "png")
    with pytest.raises(StorageError):
        await storage.save(b"x", "original", "p/ng")


async def test_staged_files_discard_removes_written_and_finalize_removes_marked(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    old = await storage.save(b"old", "cover", "png")

    failed = StagedFiles(storage)
    new_key = await failed.save(b"new", "cover", "png")
    failed.delete_after_commit([old])
    await failed.discard()
    assert await storage.read(old) == b"old"  # giao dịch thất bại: tệp cũ còn
    with pytest.raises(NotFoundError):
        await storage.read(new_key)

    ok = StagedFiles(storage)
    kept = await ok.save(b"new", "cover", "png")
    ok.delete_after_commit([old])
    await ok.finalize()
    assert await storage.read(kept) == b"new"
    with pytest.raises(NotFoundError):
        await storage.read(old)
