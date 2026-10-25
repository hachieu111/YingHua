"""Kiểm tra ảnh tải lên: định dạng thật (đọc header), đuôi, dung lượng, kích thước, sha256.

Dùng chung cho ảnh trang (F03.07), ảnh tải nhanh (F03.08), ảnh bìa (F03.04) và ảnh đại diện (F01.10).
Không tin đuôi hay Content-Type do client gửi; nội dung tệp quyết định.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.core.errors import DomainError, InvalidInputError, PayloadTooLargeError

ALLOWED_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp"})
# mime thật -> (đuôi lưu trữ, tên định dạng của Pillow)
_FORMATS: dict[str, tuple[str, str]] = {
    "image/jpeg": ("jpg", "JPEG"),
    "image/png": ("png", "PNG"),
    "image/webp": ("webp", "WEBP"),
}
# Chặn ảnh "bom giải nén"; trang truyện dọc 800x12000 chỉ khoảng 10 triệu điểm ảnh.
MAX_IMAGE_PIXELS = 60_000_000


class UnsupportedImageError(InvalidInputError):
    code = "UNSUPPORTED_IMAGE_TYPE"
    default_message = "Chỉ chấp nhận ảnh jpg, png hoặc webp"


class CorruptImageError(InvalidInputError):
    code = "INVALID_IMAGE"
    default_message = "Tệp ảnh bị hỏng hoặc không đọc được"


class ImageTooLargeError(PayloadTooLargeError):
    code = "IMAGE_TOO_LARGE"
    default_message = "Ảnh vượt quá dung lượng cho phép"


@dataclass(frozen=True, slots=True)
class ImageInfo:
    mime_type: str
    extension: str
    sha256: str
    size_bytes: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ImageUpload:
    """Ảnh đã qua kiểm tra, sẵn sàng để lưu."""

    data: bytes
    info: ImageInfo


def sniff_mime(head: bytes) -> str | None:
    """Nhận dạng định dạng từ vài byte đầu của tệp."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def filename_extension(filename: str | None) -> str:
    """Đuôi (chữ thường, không dấu chấm) của tên tệp client gửi; chỉ để kiểm tra, không làm đường dẫn."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def inspect_image(data: bytes, filename: str | None, max_bytes: int) -> ImageInfo:
    """Kiểm tra đồng bộ (CPU). Raise lỗi nghiệp vụ nếu ảnh không hợp lệ."""
    if len(data) > max_bytes:
        raise ImageTooLargeError(f"Ảnh vượt quá {max_bytes // (1024 * 1024)} MB")
    if not data:
        raise CorruptImageError("Tệp ảnh rỗng")
    if filename_extension(filename) not in ALLOWED_EXTENSIONS:
        raise UnsupportedImageError()
    mime = sniff_mime(data[:16])
    if mime is None:
        raise UnsupportedImageError()
    extension, pillow_format = _FORMATS[mime]
    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            if img.format != pillow_format:
                raise UnsupportedImageError()
            if width * height > MAX_IMAGE_PIXELS:
                raise CorruptImageError("Kích thước ảnh quá lớn")
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise CorruptImageError() from exc
    return ImageInfo(
        mime_type=mime,
        extension=extension,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        width=width,
        height=height,
    )


async def validate_image(data: bytes, filename: str | None, max_bytes: int) -> ImageUpload:
    """Như `inspect_image` nhưng chạy ngoài event loop."""
    info = await asyncio.to_thread(inspect_image, data, filename, max_bytes)
    return ImageUpload(data=data, info=info)


@dataclass(frozen=True, slots=True)
class UploadAttempt:
    """Kết quả kiểm tra một tệp trong lượt tải nhiều tệp: hoặc ảnh hợp lệ, hoặc lý do bị từ chối (F03.07)."""

    filename: str | None
    upload: ImageUpload | None = None
    error: DomainError | None = None
