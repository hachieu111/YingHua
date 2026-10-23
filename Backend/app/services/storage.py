"""Lưu file vật lý vào STORAGE_ROOT, chống trùng bằng sha256, pHash và cắt ảnh bong bóng."""

import hashlib
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import StoredFile

EXT_BY_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "audio/mpeg": ".mp3"}


def file_path(f: StoredFile) -> Path:
    return settings.storage_root / f.storage_key


def merge_expiry(current: datetime | None, wanted: datetime | None) -> datetime | None:
    """Giữ thời hạn dài hơn. None = vĩnh viễn nên luôn thắng."""
    if current is None or wanted is None:
        return None
    return max(current, wanted)


def extend_expiry(f: StoredFile | None, wanted: datetime | None) -> None:
    if f is not None:
        f.expires_at = merge_expiry(f.expires_at, wanted)


def save_bytes(db: Session, data: bytes, kind: str, mime: str, *, width: int | None = None,
               height: int | None = None, expires_at: datetime | None = None) -> StoredFile:
    sha = hashlib.sha256(data).hexdigest()
    existing = db.execute(
        select(StoredFile).where(StoredFile.kind == kind, StoredFile.sha256 == sha)
    ).scalar_one_or_none()
    if existing is not None:
        extend_expiry(existing, expires_at)
        path = file_path(existing)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return existing

    key = f"{kind}/{sha[:2]}/{sha}{EXT_BY_MIME.get(mime, '.bin')}"
    path = settings.storage_root / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    f = StoredFile(kind=kind, storage_key=key, sha256=sha, mime_type=mime, size_bytes=len(data),
                   width=width, height=height, expires_at=expires_at)
    db.add(f)
    db.flush()
    return f


def save_image(db: Session, img: np.ndarray, kind: str, *, fmt: str = ".jpg", quality: int = 92,
               expires_at: datetime | None = None) -> StoredFile:
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if fmt == ".jpg" else [cv2.IMWRITE_WEBP_QUALITY, quality]
    ok, buf = cv2.imencode(fmt, img, params)
    if not ok:
        raise ValueError("Không encode được ảnh")
    mime = "image/jpeg" if fmt == ".jpg" else "image/webp"
    h, w = img.shape[:2]
    return save_bytes(db, buf.tobytes(), kind, mime, width=w, height=h, expires_at=expires_at)


def decode_image(data: bytes) -> np.ndarray | None:
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def read_image(f: StoredFile) -> np.ndarray | None:
    path = file_path(f)
    if not path.exists():
        return None
    return decode_image(path.read_bytes())


def phash(img: np.ndarray) -> int:
    """pHash 64-bit (DCT 32x32 -> 8x8 góc trên trái, so với median), trả về int64 có dấu cho cột BIGINT."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    low = cv2.dct(small)[:8, :8]
    bits = (low > np.median(low)).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return value - (1 << 64) if value >= (1 << 63) else value


def crop_snippet(img: np.ndarray, x: int, y: int, w: int, h: int, pad: int = 12,
                 max_side: int = 480) -> np.ndarray:
    """Cắt vùng bong bóng (kèm lề) và thu nhỏ để làm ảnh ngữ cảnh trên flashcard."""
    ih, iw = img.shape[:2]
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(iw, x + w + pad), min(ih, y + h + pad)
    crop = img[y0:y1, x0:x1]
    scale = max_side / max(crop.shape[:2])
    if scale < 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return crop
