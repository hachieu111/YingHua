"""Upload trang truyện: lưu ảnh gốc, chống trùng (sha256 / pHash), tạo job dịch."""

import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Chapter, Page, Series, StoredFile, Translation
from . import storage


def _mime_of(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _natural_key(name: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name or "")]


def upload_expiry(series: Series) -> datetime | None:
    if series.visibility == "public":
        return None
    return datetime.now(timezone.utc) + timedelta(days=settings.upload_retention_days)


def _reusable_translation(db: Session, f: StoredFile, ph: int) -> Translation | None:
    t = db.execute(
        select(Translation).where(Translation.source_file_id == f.id,
                                  Translation.status.in_(("queued", "running", "done")))
        .order_by(Translation.id.desc()).limit(1)
    ).scalar_one_or_none()
    if t is not None:
        return t
    # Ảnh gần giống (nén lại, đổi định dạng) nhưng cùng kích thước -> toạ độ bong bóng vẫn đúng
    row = db.execute(text("""
        SELECT t.id FROM translations t
        JOIN stored_files f ON f.id = t.source_file_id
        WHERE t.status = 'done' AND t.phash IS NOT NULL AND t.rendered_file_id IS NOT NULL
          AND f.width = :w AND f.height = :h
          AND bit_count((t.phash # :p)::bit(64)) <= :d
        ORDER BY bit_count((t.phash # :p)::bit(64)), t.id DESC
        LIMIT 1"""), {"w": f.width, "h": f.height, "p": ph, "d": settings.phash_max_distance}).first()
    return db.get(Translation, row[0]) if row else None


def add_pages(db: Session, chapter: Chapter, files: list[tuple[str, bytes]]) -> tuple[list[Page], list[int]]:
    """Trả về (các trang mới, các translation_id cần đưa vào hàng đợi)."""
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Chưa chọn ảnh")
    series = chapter.series
    expires = upload_expiry(series)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    next_no = (db.execute(select(func.max(Page.page_no)).where(Page.chapter_id == chapter.id)).scalar() or 0) + 1

    pages, jobs = [], []
    for name, data in sorted(files, key=lambda x: _natural_key(x[0])):
        if len(data) > max_bytes:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                f"{name}: vượt quá {settings.max_upload_mb} MB")
        img = storage.decode_image(data)
        if img is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{name}: không đọc được ảnh")
        h, w = img.shape[:2]
        mime = _mime_of(data)
        if mime is None:  # định dạng lạ (bmp, tiff...) -> lưu lại dạng JPEG
            f = storage.save_image(db, img, "original", expires_at=expires)
        else:
            f = storage.save_bytes(db, data, "original", mime, width=w, height=h, expires_at=expires)
        ph = storage.phash(img)

        t = _reusable_translation(db, f, ph)
        if t is None:
            t = Translation(source_file_id=f.id, phash=ph, status="queued",
                            pipeline_version=settings.pipeline_version)
            db.add(t)
            db.flush()
            jobs.append(t.id)
        else:
            # Trang mới dùng chung bản dịch -> giữ các file của bản dịch ít nhất lâu bằng trang này
            for fid in (t.source_file_id, t.inpainted_file_id, t.rendered_file_id):
                storage.extend_expiry(db.get(StoredFile, fid) if fid else None, expires)

        page = Page(chapter_id=chapter.id, page_no=next_no, original_file_id=f.id, translation_id=t.id,
                    width=w, height=h)
        db.add(page)
        pages.append(page)
        next_no += 1
    db.flush()
    return pages, jobs


def quick_upload_chapter(db: Session, user_id: int) -> Chapter:
    """Series riêng 'Ảnh tải lên của tôi' + 1 chương mới cho mỗi lần tải nhanh."""
    s = db.execute(select(Series).where(Series.owner_id == user_id, Series.title_vi == "Ảnh tải lên của tôi")
                   .order_by(Series.id).limit(1)).scalar_one_or_none()
    if s is None:
        s = Series(owner_id=user_id, visibility="private", title_vi="Ảnh tải lên của tôi",
                   description="Các trang bạn tải lên nhanh. Ảnh được giữ 7 ngày.")
        db.add(s)
        db.flush()
    last = db.execute(select(func.max(Chapter.number)).where(Chapter.series_id == s.id)).scalar() or 0
    c = Chapter(series_id=s.id, number=int(last) + 1,
                title="Tải lên " + datetime.now().strftime("%d/%m/%Y %H:%M"))  # strftime trên Windows lỗi với chữ có dấu
    db.add(c)
    db.flush()
    db.refresh(c)
    return c
