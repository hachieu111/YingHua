"""Cắt ảnh ngữ cảnh (bong bóng) từ ảnh gốc của trang bằng Pillow — việc CPU nên chạy ngoài event loop."""

from __future__ import annotations

import asyncio
import io

from PIL import Image, UnidentifiedImageError

from app.core.image_validation import CorruptImageError, ImageUpload, validate_image
from app.modules.vocab.domain.entities import CropBox
from app.modules.vocab.domain.rules import SNIPPET_MAX_SIDE_PX

SNIPPET_FILENAME = "snippet.png"  # chỉ để qua bộ kiểm tra ảnh; không dùng làm đường dẫn


def _crop(image: bytes, box: CropBox) -> bytes:
    try:
        with Image.open(io.BytesIO(image)) as source:
            cropped = source.crop((box.left, box.top, box.right, box.bottom)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise CorruptImageError() from exc
    cropped.thumbnail((SNIPPET_MAX_SIDE_PX, SNIPPET_MAX_SIDE_PX))
    buffer = io.BytesIO()
    cropped.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


class PillowSnippetCropper:
    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes

    async def crop(self, image: bytes, box: CropBox) -> ImageUpload:
        data = await asyncio.to_thread(_crop, image, box)
        return await validate_image(data, SNIPPET_FILENAME, self._max_bytes)
