"""Giải mã / mã hóa ảnh và perceptual hash cho worker (hàm thuần, chạy trong luồng xử lý ảnh)."""

from __future__ import annotations

import cv2
import numpy as np

from worker.pipeline_types import ImageArray

JPEG_QUALITY = 92
PHASH_DCT_SIZE = 32
PHASH_LOW_FREQ = 8
_INT64_SIGN = 1 << 63
_UINT64_RANGE = 1 << 64


def decode_image(data: bytes) -> ImageArray | None:
    """Ảnh BGR 3 kênh, hoặc None nếu bytes không phải ảnh đọc được."""
    if not data:
        return None
    buf = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        return None
    return np.asarray(img, dtype=np.uint8)


def encode_jpeg(img: ImageArray) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise ValueError("cv2.imencode không mã hóa được ảnh")
    return bytes(buf.tobytes())


def phash(img: ImageArray) -> int:
    """pHash 64-bit (DCT 32x32 → góc 8x8, so với trung vị), đổi sang int64 có dấu cho cột BIGINT.

    Cùng thuật toán với `Backend/app/services/storage.phash` để giá trị hai bản so sánh được với nhau.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    size = (PHASH_DCT_SIZE, PHASH_DCT_SIZE)
    small = cv2.resize(gray, size, interpolation=cv2.INTER_AREA).astype(np.float32)
    low = cv2.dct(small)[:PHASH_LOW_FREQ, :PHASH_LOW_FREQ]
    bits = (low > np.median(low)).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value - _UINT64_RANGE if value >= _INT64_SIGN else value
