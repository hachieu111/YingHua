"""Gợi ý từ vựng theo chương."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, VocabSuggestion
from ..security import get_current_user
from ..services import access, suggestions
from ..services.vocab import add_vocab, vocab_out

router = APIRouter(prefix="/api", tags=["suggestions"])


@router.get("/chapters/{chapter_id}/suggestions")
def chapter_suggestions(chapter_id: int, limit: int = Query(15, ge=1, le=50),
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tính lại gợi ý cho chương dựa trên từ trong chương + lịch sử tra cứu + trình độ."""
    access.get_chapter(db, chapter_id, user)
    items = suggestions.generate(db, user, chapter_id, limit)
    db.commit()
    return [suggestions.suggestion_out(db, s) for s in items]


def _own(db: Session, sid: int, user: User) -> VocabSuggestion:
    s = db.get(VocabSuggestion, sid)
    if s is None or s.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy gợi ý")
    return s


@router.post("/suggestions/{suggestion_id}/accept")
def accept(suggestion_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Thêm từ gợi ý vào sổ tay (kèm ngữ cảnh lần xuất hiện đầu tiên trong chương)."""
    s = _own(db, suggestion_id, user)
    first = suggestions.suggestion_out(db, s)["first_bubble_id"]
    v, _ = add_vocab(db, user, term=s.term, bubble_id=first, custom_meaning=None, note=None,
                     source="suggestion", card_types=["recognition", "recall"])
    s.status = "accepted"
    db.commit()
    db.refresh(v)
    return vocab_out(db, v)


@router.post("/suggestions/{suggestion_id}/dismiss", status_code=204)
def dismiss(suggestion_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _own(db, suggestion_id, user).status = "dismissed"
    db.commit()
