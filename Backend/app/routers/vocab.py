"""Sổ tay từ vựng cá nhân."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import StoredFile, User, UserVocab, VocabContext
from ..schemas import ContextIn, VocabIn, VocabPatch
from ..security import get_current_user
from ..services import storage
from ..services.vocab import add_context, add_vocab, context_out, get_own_vocab, vocab_out

router = APIRouter(prefix="/api/vocab", tags=["vocab"])


@router.get("")
def list_vocab(status_: Literal["learning", "known", "ignored"] | None = Query(None, alias="status"),
               q: str | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(UserVocab).where(UserVocab.user_id == user.id)
    if status_:
        stmt = stmt.where(UserVocab.status == status_)
    if q:
        stmt = stmt.where(or_(UserVocab.term.contains(q), UserVocab.custom_meaning.ilike(f"%{q}%"),
                              UserVocab.note.ilike(f"%{q}%")))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar()
    rows = db.execute(stmt.order_by(UserVocab.created_at.desc()).offset((page - 1) * size).limit(size)).scalars()
    return {"total": total, "page": page, "size": size, "items": [vocab_out(db, v) for v in rows]}


@router.post("", status_code=201)
def create_vocab(body: VocabIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lưu từ (thường là chữ vừa bôi đen). Có bubble_id thì lưu kèm câu + ảnh cắt bong bóng.
    Gọi lại với từ đã có: chỉ thêm ngữ cảnh mới, không tạo trùng."""
    v, created = add_vocab(db, user, term=body.term, bubble_id=body.bubble_id, custom_meaning=body.custom_meaning,
                           note=body.note, source=body.source, card_types=body.card_types)
    db.commit()
    db.refresh(v)
    return {**vocab_out(db, v, detail=True), "created": created}


@router.get("/{vocab_id}")
def get_vocab(vocab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return vocab_out(db, get_own_vocab(db, vocab_id, user), detail=True)


@router.patch("/{vocab_id}")
def patch_vocab(vocab_id: int, body: VocabPatch, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    v = get_own_vocab(db, vocab_id, user)
    data = body.model_dump(exclude_unset=True)
    for k, val in data.items():
        setattr(v, k, val)
    if "status" in data:
        # Đã thuộc / bỏ qua -> tạm ngưng ôn tập; học lại -> mở lại thẻ
        for c in v.flashcards:
            c.suspended = v.status != "learning"
    db.commit()
    db.refresh(v)
    return vocab_out(db, v, detail=True)


@router.delete("/{vocab_id}", status_code=204)
def delete_vocab(vocab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(get_own_vocab(db, vocab_id, user))
    db.commit()


@router.post("/{vocab_id}/contexts", status_code=201)
def create_context(vocab_id: int, body: ContextIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    v = get_own_vocab(db, vocab_id, user)
    ctx = add_context(db, user, v, body.bubble_id)
    db.commit()
    return context_out(ctx)


def _own_context(db: Session, context_id: int, user: User) -> VocabContext:
    c = db.get(VocabContext, context_id)
    if c is None or db.get(UserVocab, c.user_vocab_id).user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy ngữ cảnh")
    return c


@router.delete("/contexts/{context_id}", status_code=204)
def delete_context(context_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own_context(db, context_id, user))
    db.commit()


@router.get("/contexts/{context_id}/snippet")
def context_snippet(context_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ảnh cắt bong bóng (.webp) để hiện ở mặt sau flashcard."""
    c = _own_context(db, context_id, user)
    f = db.get(StoredFile, c.snippet_file_id) if c.snippet_file_id else None
    if f is None or not storage.file_path(f).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ngữ cảnh này không có ảnh")
    return FileResponse(storage.file_path(f), media_type=f.mime_type)
