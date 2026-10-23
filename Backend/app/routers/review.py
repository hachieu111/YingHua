"""Ôn tập flashcard theo SM-2."""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Flashcard, ReviewLog, User, UserSettings
from ..schemas import FlashcardPatch, ReviewIn
from ..security import get_current_user
from ..services import dictionary, srs
from ..services.vocab import card_brief, context_out

router = APIRouter(prefix="/api", tags=["review"])


def _own_card(db: Session, card_id: int, user: User) -> Flashcard:
    c = db.get(Flashcard, card_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy thẻ")
    return c


def _fmt_interval(days: float) -> str:
    if days < 1 / 24:
        return f"{round(days * 1440)} phút"
    if days < 1:
        return f"{round(days * 24)} giờ"
    if days < 30:
        return f"{round(days)} ngày"
    if days < 365:
        return f"{round(days / 30, 1)} tháng"
    return f"{round(days / 365, 1)} năm"


def _card_out(db: Session, c: Flashcard, now: datetime) -> dict:
    v = c.vocab
    ctx = v.contexts[-1] if v.contexts else None
    meaning = v.custom_meaning or dictionary.summary_meaning(db, v.term)
    preview = {}
    for r in (1, 2, 3, 4):
        s = srs.next_schedule(state=c.state, interval_days=c.interval_days, ease_factor=c.ease_factor,
                              reps=c.reps, lapses=c.lapses, rating=r, now=now)
        preview[r] = _fmt_interval(s.interval_days)
    return {
        **card_brief(c),
        "vocab": {"id": v.id, "term": v.term, "pinyin": dictionary.pinyin_of(v.term),
                  "han_viet": v.entry.han_viet if v.entry else None, "meaning": meaning, "note": v.note},
        "context": context_out(ctx) if ctx else None,
        "audio_url": f"/api/tts?text={quote(v.term)}",
        # recognition: mặt trước = chữ Hán | recall: mặt trước = nghĩa Việt | listening: mặt trước = âm thanh
        "front": {"recognition": "term", "recall": "meaning", "listening": "audio"}[c.card_type],
        "interval_preview": preview,
    }


@router.get("/review/due")
def due_cards(limit: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """Thẻ cần ôn bây giờ: thẻ đến hạn trước, sau đó thẻ mới (theo hạn mức/ngày trong cài đặt)."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    st = db.get(UserSettings, user.id)
    cap, new_per_day = (st.daily_review_cap, st.daily_new_cards) if st else (100, 10)
    reviewed_today, new_today = db.execute(select(
        func.count(), func.count().filter(ReviewLog.state_before == "new"))
        .where(ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= day_start)).one()

    review_quota = max(0, cap - reviewed_today)
    due = db.execute(select(Flashcard).where(
        Flashcard.user_id == user.id, Flashcard.suspended.is_(False), Flashcard.state != "new",
        Flashcard.due_at <= now).order_by(Flashcard.due_at).limit(min(limit, review_quota))).scalars().all()
    new_quota = max(0, min(limit - len(due), new_per_day - new_today))
    new = db.execute(select(Flashcard).where(
        Flashcard.user_id == user.id, Flashcard.suspended.is_(False), Flashcard.state == "new")
        .order_by(Flashcard.created_at, Flashcard.id).limit(new_quota)).scalars().all() if new_quota else []

    total_due = db.execute(select(func.count()).select_from(Flashcard).where(
        Flashcard.user_id == user.id, Flashcard.suspended.is_(False), Flashcard.state != "new",
        Flashcard.due_at <= now)).scalar()
    return {
        "cards": [_card_out(db, c, now) for c in [*due, *new]],
        "counts": {"due": total_due, "new_today_left": max(0, new_per_day - new_today),
                   "reviewed_today": reviewed_today},
    }


@router.post("/review/{card_id}")
def review(card_id: int, body: ReviewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _own_card(db, card_id, user)
    now = datetime.now(timezone.utc)
    s = srs.next_schedule(state=c.state, interval_days=c.interval_days, ease_factor=c.ease_factor,
                          reps=c.reps, lapses=c.lapses, rating=body.rating, now=now)
    db.add(ReviewLog(card_id=c.id, user_id=user.id, rating=body.rating, state_before=c.state,
                     interval_before=c.interval_days, interval_after=s.interval_days, ease_after=s.ease_factor,
                     duration_ms=body.duration_ms, reviewed_at=now))
    c.state, c.interval_days, c.ease_factor = s.state, s.interval_days, s.ease_factor
    c.reps, c.lapses, c.due_at, c.last_reviewed_at = s.reps, s.lapses, s.due_at, now
    db.commit()
    return {**card_brief(c), "next_in": _fmt_interval(s.interval_days)}


@router.patch("/flashcards/{card_id}")
def patch_card(card_id: int, body: FlashcardPatch, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    c = _own_card(db, card_id, user)
    c.suspended = body.suspended
    db.commit()
    return card_brief(c)


@router.post("/flashcards/{card_id}/reset")
def reset_card(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Học lại thẻ từ đầu (giữ lịch sử ôn)."""
    c = _own_card(db, card_id, user)
    c.state, c.interval_days, c.ease_factor, c.reps, c.lapses = "new", 0, 2.5, 0, 0
    c.due_at = datetime.now(timezone.utc)
    db.commit()
    return card_brief(c)


@router.get("/review/history")
def history(days: int = Query(30, ge=1, le=365), user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    """Số lượt ôn và tỉ lệ nhớ theo ngày."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(select(func.date(ReviewLog.reviewed_at), func.count(),
                             func.count().filter(ReviewLog.rating >= 3))
                      .where(ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= since)
                      .group_by(func.date(ReviewLog.reviewed_at)).order_by(func.date(ReviewLog.reviewed_at))).all()
    return [{"date": d.isoformat(), "reviews": n, "correct": ok, "retention": round(ok / n, 3)} for d, n, ok in rows]
