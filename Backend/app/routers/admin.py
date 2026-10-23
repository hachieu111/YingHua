"""Quản trị: người dùng, hàng đợi dịch, thống kê hệ thống."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Page, Series, StoredFile, Translation, User, UserVocab
from ..schemas import AdminUserPatch, UserOut
from ..security import require_admin, revoke_all_for_user
from ..services.pipeline_runner import worker

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(q: str | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
               admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(User)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.display_name.ilike(f"%{q}%")))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar()
    rows = db.execute(stmt.order_by(User.id).offset((page - 1) * size).limit(size)).scalars()
    return {"total": total, "items": [UserOut.model_validate(u) for u in rows]}


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(user_id: int, body: AdminUserPatch, admin: User = Depends(require_admin),
               db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy người dùng")
    if u.id == admin.id and (body.role == "user" or body.is_active is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không tự hạ quyền hoặc khoá chính mình")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    if body.is_active is False:
        revoke_all_for_user(db, u.id)
    db.commit()
    return u


@router.get("/translations")
def list_translations(status_: Literal["queued", "running", "done", "failed"] | None = Query(None, alias="status"),
                      limit: int = Query(50, le=200), admin: User = Depends(require_admin),
                      db: Session = Depends(get_db)):
    stmt = select(Translation)
    if status_:
        stmt = stmt.where(Translation.status == status_)
    rows = db.execute(stmt.order_by(Translation.id.desc()).limit(limit)).scalars()
    return [{"id": t.id, "status": t.status, "mode": t.mode, "error": (t.error or "")[-500:] or None,
             "processing_ms": t.processing_ms, "created_at": t.created_at, "finished_at": t.finished_at}
            for t in rows]


@router.post("/translations/{translation_id}/retry")
def retry(translation_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.get(Translation, translation_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bản dịch")
    if t.status in ("queued", "running"):
        return {"id": t.id, "status": t.status}
    t.status = "queued"
    t.error = None
    db.commit()
    worker.enqueue(t.id)
    return {"id": t.id, "status": t.status}


@router.get("/stats")
def stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    count = lambda m: db.execute(select(func.count()).select_from(m)).scalar()  # noqa: E731
    by_status = dict(db.execute(select(Translation.status, func.count()).group_by(Translation.status)).all())
    storage_rows = db.execute(select(StoredFile.kind, func.count(), func.coalesce(func.sum(StoredFile.size_bytes), 0))
                              .group_by(StoredFile.kind)).all()
    return {
        "users": count(User), "series": count(Series), "pages": count(Page), "vocab": count(UserVocab),
        "translations": by_status,
        "storage": {k: {"files": n, "mb": round(b / 1024 / 1024, 2)} for k, n, b in storage_rows},
        "pipeline": worker.status(),
    }
