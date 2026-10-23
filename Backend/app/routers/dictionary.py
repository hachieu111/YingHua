"""Tra từ (từ điển đầy đủ + bộ tu tiên tách riêng), phân rã chữ Hán, nét viết, tách từ, ghi sự kiện."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import LookupEvent, User, UserVocab
from ..schemas import EventIn, SegmentIn
from ..security import get_current_user
from ..services import access, dictionary

router = APIRouter(prefix="/api/dict", tags=["dictionary"])


def _log(db: Session, user: User, term: str, action: str, bubble_id: int | None, entry_id: int | None = None):
    if bubble_id is not None:
        access.get_bubble(db, bubble_id, user)  # chỉ ghi khi user xem được bong bóng
    db.add(LookupEvent(user_id=user.id, term=term[:32], entry_id=entry_id, bubble_id=bubble_id, action=action))


@router.get("/lookup")
def lookup(term: str = Query(min_length=1, max_length=32), bubble_id: int | None = None, log: bool = True,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tra 1 từ/cụm (vd: chữ vừa bôi đen). Tự ghi lịch sử tra cứu để cá nhân hoá."""
    term = term.strip()
    if not dictionary.has_cjk(term):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cần nhập chữ Hán")
    data = dictionary.lookup(db, term)
    v = db.execute(select(UserVocab).where(UserVocab.user_id == user.id, UserVocab.term == term)).scalar_one_or_none()
    data["in_vocab"] = {"id": v.id, "status": v.status} if v else None
    if log:
        _log(db, user, term, "lookup", bubble_id, data["entries"][0]["id"] if data["entries"] else None)
        db.commit()
    return data


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=64), limit: int = Query(20, le=100),
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tìm trong từ điển đầy đủ theo chữ Hán (tiền tố), pinyin (có/không số thanh) hoặc âm Hán Việt."""
    return dictionary.search(db, q, limit)


@router.get("/xianxia/search")
def search_xianxia(q: str = Query(min_length=1, max_length=32), kind: Literal["phrase", "name", "char"] | None = None,
                   limit: int = Query(20, le=100), user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Tìm trong bộ từ điển tu tiên (VietPhrase / Names / PhienAm), tách riêng khỏi từ điển đầy đủ."""
    return dictionary.search_xianxia(db, q, kind, limit)


@router.get("/hanzi/{ch}")
def hanzi(ch: str, strokes: bool = True, log: bool = True, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    """Phân rã 1 chữ Hán: bộ thủ, cấu tạo, nguồn gốc, và dữ liệu nét để vẽ thứ tự viết.

    stroke_data.strokes: các path SVG trong hệ toạ độ 1024x1024 (trục y lật: dùng transform
    "scale(1,-1) translate(0,-900)"); stroke_data.medians: đường giữa từng nét để làm animation.
    """
    if len(ch) != 1 or not ch.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Chỉ nhận 1 chữ Hán")
    data = dictionary.hanzi_info(db, ch, with_strokes=strokes)
    if log:
        _log(db, user, ch, "decompose", None)
        db.commit()
    return data


@router.post("/segment")
def segment(body: SegmentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tách câu thành từ (jieba) kèm pinyin và nghĩa ngắn."""
    return dictionary.segment(db, body.text)


@router.post("/events", status_code=204)
def log_event(body: EventIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Frontend ghi sự kiện hover / tts ... (lookup và decompose được ghi tự động)."""
    _log(db, user, body.term.strip(), body.action, body.bubble_id)
    db.commit()
