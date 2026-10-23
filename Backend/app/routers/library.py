"""Truyện / chương / trang: thư viện chung (admin) + truyện tự upload (riêng tư, giữ 7 ngày)."""

from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import (Bubble, BubbleEdit, Chapter, Page, ReadingProgress, Series, StoredFile, Translation,
                      User)
from ..schemas import (BubbleEditIn, ChapterIn, ChapterOut, ChapterPatch, ProgressIn, SeriesIn, SeriesOut,
                       SeriesPatch)
from ..security import get_current_user
from ..services import access, library, storage
from ..services.pipeline_runner import worker

router = APIRouter(prefix="/api", tags=["library"])


# ------------------------------------------------------------------ helpers
def _series_out(db: Session, s: Series) -> dict:
    n = db.execute(select(func.count()).select_from(Chapter).where(Chapter.series_id == s.id)).scalar()
    return {**SeriesOut.model_validate(s).model_dump(), "chapter_count": n}


def _chapter_out(db: Session, c: Chapter) -> dict:
    n = db.execute(select(func.count()).select_from(Page).where(Page.chapter_id == c.id)).scalar()
    return {**ChapterOut.model_validate(c).model_dump(), "page_count": n}


def _file_alive(db: Session, file_id: int | None) -> bool:
    if not file_id:
        return False
    f = db.get(StoredFile, file_id)
    return f is not None and storage.file_path(f).exists()


def _page_summary(db: Session, p: Page) -> dict:
    t = p.translation
    return {
        "id": p.id, "page_no": p.page_no, "width": p.width, "height": p.height,
        "translation_id": p.translation_id,
        "status": t.status if t else "missing",
        "has_original": _file_alive(db, p.original_file_id),
        "has_rendered": bool(t and _file_alive(db, t.rendered_file_id)),
        "expires_at": p.original_file.expires_at if p.original_file else None,
    }


def _commit_and_enqueue(db: Session, jobs: list[int]):
    db.commit()
    for tid in jobs:
        worker.enqueue(tid)


# ------------------------------------------------------------------ series
@router.get("/series")
def list_series(scope: Literal["all", "public", "mine"] = "all", q: str | None = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Series)
    if scope == "public":
        stmt = stmt.where(Series.visibility == "public")
    elif scope == "mine":
        stmt = stmt.where(Series.owner_id == user.id)
    elif user.role != "admin":
        stmt = stmt.where(or_(Series.visibility == "public", Series.owner_id == user.id))
    if q:
        stmt = stmt.where(or_(Series.title_vi.ilike(f"%{q}%"), Series.title_zh.ilike(f"%{q}%")))
    rows = db.execute(stmt.order_by(Series.created_at.desc())).scalars().all()
    return [_series_out(db, s) for s in rows]


@router.post("/series", status_code=201)
def create_series(body: SeriesIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.public and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chỉ admin được đăng truyện vào thư viện chung")
    s = Series(owner_id=None if body.public else user.id, visibility="public" if body.public else "private",
               title_vi=body.title_vi.strip(), title_zh=body.title_zh, description=body.description,
               status=body.status)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _series_out(db, s)


@router.get("/series/{series_id}")
def get_series(series_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = access.get_series(db, series_id, user)
    chapters = db.execute(select(Chapter).where(Chapter.series_id == s.id).order_by(Chapter.number)).scalars().all()
    progress = {p.chapter_id: p for p in db.execute(select(ReadingProgress).where(
        ReadingProgress.user_id == user.id, ReadingProgress.chapter_id.in_([c.id for c in chapters]))).scalars()}
    out = []
    for c in chapters:
        p = progress.get(c.id)
        out.append({**_chapter_out(db, c), "progress": {"last_page_no": p.last_page_no, "mode": p.mode,
                                                        "completed": p.completed} if p else None})
    return {**_series_out(db, s), "can_edit": access.can_edit(user, s), "chapters": out}


@router.patch("/series/{series_id}")
def patch_series(series_id: int, body: SeriesPatch, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    s = access.get_series(db, series_id, user, edit=True)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    return _series_out(db, s)


@router.delete("/series/{series_id}", status_code=204)
def delete_series(series_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(access.get_series(db, series_id, user, edit=True))
    db.commit()


# ------------------------------------------------------------------ chapters
@router.post("/series/{series_id}/chapters", status_code=201)
def create_chapter(series_id: int, body: ChapterIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    s = access.get_series(db, series_id, user, edit=True)
    c = Chapter(series_id=s.id, number=body.number, title=body.title)
    db.add(c)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Số chương đã tồn tại trong truyện này")
    db.refresh(c)
    return _chapter_out(db, c)


@router.get("/chapters/{chapter_id}")
def get_chapter(chapter_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = access.get_chapter(db, chapter_id, user)
    pages = db.execute(select(Page).where(Page.chapter_id == c.id).order_by(Page.page_no)).scalars().all()
    p = db.get(ReadingProgress, (user.id, c.id))
    siblings = db.execute(select(Chapter.id, Chapter.number).where(Chapter.series_id == c.series_id)
                          .order_by(Chapter.number)).all()
    ids = [i for i, _ in siblings]
    pos = ids.index(c.id)
    return {
        **_chapter_out(db, c),
        "series": {"id": c.series.id, "title_vi": c.series.title_vi, "visibility": c.series.visibility},
        "can_edit": access.can_edit(user, c.series),
        "prev_chapter_id": ids[pos - 1] if pos > 0 else None,
        "next_chapter_id": ids[pos + 1] if pos + 1 < len(ids) else None,
        "progress": {"last_page_no": p.last_page_no, "mode": p.mode, "completed": p.completed} if p else None,
        "pages": [_page_summary(db, pg) for pg in pages],
    }


@router.patch("/chapters/{chapter_id}")
def patch_chapter(chapter_id: int, body: ChapterPatch, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    c = access.get_chapter(db, chapter_id, user, edit=True)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Số chương đã tồn tại trong truyện này")
    return _chapter_out(db, c)


@router.delete("/chapters/{chapter_id}", status_code=204)
def delete_chapter(chapter_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(access.get_chapter(db, chapter_id, user, edit=True))
    db.commit()


@router.put("/chapters/{chapter_id}/progress")
def save_progress(chapter_id: int, body: ProgressIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    c = access.get_chapter(db, chapter_id, user)
    p = db.get(ReadingProgress, (user.id, c.id))
    if p is None:
        p = ReadingProgress(user_id=user.id, chapter_id=c.id)
        db.add(p)
    p.last_page_no, p.mode, p.completed = body.last_page_no, body.mode, body.completed
    db.commit()
    return {"chapter_id": c.id, "last_page_no": p.last_page_no, "mode": p.mode, "completed": p.completed}


# ------------------------------------------------------------------ upload
async def _read_files(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    return [(f.filename or "page.jpg", await f.read()) for f in files]


@router.post("/chapters/{chapter_id}/pages", status_code=201)
async def upload_pages(chapter_id: int, files: list[UploadFile] = File(...),
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Thêm trang vào cuối chương (sắp theo tên file). Mỗi trang được đưa vào hàng đợi dịch."""
    c = access.get_chapter(db, chapter_id, user, edit=True)
    pages, jobs = library.add_pages(db, c, await _read_files(files))
    _commit_and_enqueue(db, jobs)
    return {"chapter_id": c.id, "queued": len(jobs), "reused": len(pages) - len(jobs),
            "pages": [_page_summary(db, p) for p in pages]}


@router.post("/uploads/quick", status_code=201)
async def quick_upload(files: list[UploadFile] = File(...), user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Tải nhanh: tự tạo chương mới trong truyện riêng 'Ảnh tải lên của tôi'."""
    data = await _read_files(files)
    c = library.quick_upload_chapter(db, user.id)
    pages, jobs = library.add_pages(db, c, data)
    _commit_and_enqueue(db, jobs)
    return {"series_id": c.series_id, "chapter_id": c.id, "queued": len(jobs), "reused": len(pages) - len(jobs),
            "pages": [_page_summary(db, p) for p in pages]}


# ------------------------------------------------------------------ pages
@router.get("/pages/{page_id}")
def get_page(page_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dữ liệu cho cả 2 chế độ: Đọc (ảnh rendered) và Học (ảnh gốc + lớp chữ để hover/bôi đen)."""
    p = access.get_page(db, page_id, user)
    t = p.translation
    edits = {}
    bubbles = []
    if t and t.status == "done":
        ids = [b.id for b in t.bubbles]
        edits = {e.bubble_id: e.text_vi for e in db.execute(select(BubbleEdit).where(
            BubbleEdit.user_id == user.id, BubbleEdit.bubble_id.in_(ids))).scalars()} if ids else {}
        bubbles = [{
            "id": b.id, "idx": b.idx, "class_name": b.class_name,
            "x": b.x, "y": b.y, "w": b.w, "h": b.h, "polygon": b.polygon, "confidence": b.confidence,
            "text_zh": b.text_zh, "pinyin": b.pinyin,
            "text_vi": edits.get(b.id, b.text_vi), "text_vi_original": b.text_vi, "edited": b.id in edits,
            "lines": b.lines, "tokens": b.tokens,
        } for b in t.bubbles]
    pages_in_chapter = db.execute(select(Page.id, Page.page_no).where(Page.chapter_id == p.chapter_id)
                                  .order_by(Page.page_no)).all()
    ids_order = [i for i, _ in pages_in_chapter]
    pos = ids_order.index(p.id)
    return {
        **_page_summary(db, p),
        "chapter_id": p.chapter_id,
        "series_id": p.chapter.series_id,
        "prev_page_id": ids_order[pos - 1] if pos > 0 else None,
        "next_page_id": ids_order[pos + 1] if pos + 1 < len(ids_order) else None,
        "translation": {
            "id": t.id, "status": t.status, "mode": t.mode, "error": t.error, "stats": t.stats,
            "processing_ms": t.processing_ms, "finished_at": t.finished_at,
        } if t else None,
        "images": {
            "original": f"/api/pages/{p.id}/image/original",
            "rendered": f"/api/pages/{p.id}/image/rendered",
            "inpainted": f"/api/pages/{p.id}/image/inpainted",
        },
        "bubbles": bubbles,
    }


@router.get("/pages/{page_id}/image/{variant}")
def page_image(page_id: int, variant: Literal["original", "rendered", "inpainted"], download: bool = False,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = access.get_page(db, page_id, user)
    t = p.translation
    fid = {"original": p.original_file_id,
           "rendered": t.rendered_file_id if t else None,
           "inpainted": t.inpainted_file_id if t else None}[variant]
    f = db.get(StoredFile, fid) if fid else None
    if f is None or not storage.file_path(f).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Ảnh chưa sẵn sàng hoặc đã hết hạn lưu trữ" if variant != "original" else "Ảnh đã hết hạn lưu trữ")
    ext = storage.file_path(f).suffix
    name = f"chuong{access.fmt_number(p.chapter.number)}_trang{p.page_no:03d}_{variant}{ext}"
    return FileResponse(storage.file_path(f), media_type=f.mime_type,
                        filename=name if download else None,
                        content_disposition_type="attachment" if download else "inline")


@router.delete("/pages/{page_id}", status_code=204)
def delete_page(page_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(access.get_page(db, page_id, user, edit=True))
    db.commit()


@router.post("/pages/{page_id}/retranslate")
def retranslate(page_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Chạy lại pipeline cho trang (vd: lần trước lỗi, hoặc bộ dịch đã được cập nhật)."""
    p = access.get_page(db, page_id, user, edit=True)
    if not _file_alive(db, p.original_file_id):
        raise HTTPException(status.HTTP_410_GONE, "Ảnh gốc đã hết hạn lưu trữ, không dịch lại được")
    t = p.translation
    if t and t.status in ("queued", "running"):
        return {"translation_id": t.id, "status": t.status}
    t = Translation(source_file_id=p.original_file_id, phash=t.phash if t else None, status="queued",
                    pipeline_version=settings.pipeline_version)
    db.add(t)
    db.flush()
    p.translation_id = t.id
    _commit_and_enqueue(db, [t.id])
    return {"translation_id": t.id, "status": t.status}


@router.get("/translations/{translation_id}")
def translation_status(translation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.get(Translation, translation_id)
    page = db.execute(select(Page).where(Page.translation_id == translation_id).limit(1)).scalar_one_or_none() \
        if t else None
    if t is None or page is None or not access.can_view(user, page.chapter.series):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bản dịch")
    queue_pos = None
    if t.status == "queued":
        queue_pos = db.execute(select(func.count()).select_from(Translation).where(
            Translation.status == "queued", Translation.id < t.id)).scalar() + 1
    return {"id": t.id, "status": t.status, "mode": t.mode, "error": t.error, "stats": t.stats,
            "processing_ms": t.processing_ms, "finished_at": t.finished_at, "queue_position": queue_pos}


# ------------------------------------------------------------------ bubble edits
@router.put("/bubbles/{bubble_id}/edit")
def edit_bubble(bubble_id: int, body: BubbleEditIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Sửa câu dịch cho riêng mình (bản dịch gốc và người khác không bị ảnh hưởng)."""
    b, _ = access.get_bubble(db, bubble_id, user)
    e = db.get(BubbleEdit, (user.id, b.id))
    if e is None:
        e = BubbleEdit(user_id=user.id, bubble_id=b.id, text_vi=body.text_vi)
        db.add(e)
    else:
        e.text_vi = body.text_vi
    db.commit()
    return {"bubble_id": b.id, "text_vi": e.text_vi, "text_vi_original": b.text_vi, "edited": True}


@router.delete("/bubbles/{bubble_id}/edit", status_code=204)
def reset_bubble(bubble_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b, _ = access.get_bubble(db, bubble_id, user)
    e = db.get(BubbleEdit, (user.id, b.id))
    if e is not None:
        db.delete(e)
        db.commit()
