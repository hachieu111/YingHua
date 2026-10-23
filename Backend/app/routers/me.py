"""Cài đặt cá nhân, tiến độ đọc, thống kê học tập."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (Chapter, Flashcard, LookupEvent, ReadingProgress, ReviewLog, Series, User, UserSettings,
                      UserVocab)
from ..schemas import SettingsIn, SettingsOut
from ..security import get_current_user
from ..services.access import fmt_number

router = APIRouter(prefix="/api/me", tags=["me"])


def _settings(db: Session, user: User) -> UserSettings:
    st = db.get(UserSettings, user.id)
    if st is None:
        st = UserSettings(user_id=user.id)
        db.add(st)
        db.commit()
        db.refresh(st)
    return st


@router.get("/settings", response_model=SettingsOut)
def get_settings_(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _settings(db, user)


@router.put("/settings", response_model=SettingsOut)
def put_settings(body: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    st = _settings(db, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    db.commit()
    db.refresh(st)
    return st


@router.get("/progress")
def my_progress(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Các chương đang đọc dở, mới nhất trước (nút 'Đọc tiếp')."""
    rows = db.execute(
        select(ReadingProgress, Chapter, Series)
        .join(Chapter, Chapter.id == ReadingProgress.chapter_id)
        .join(Series, Series.id == Chapter.series_id)
        .where(ReadingProgress.user_id == user.id)
        .order_by(ReadingProgress.updated_at.desc()).limit(limit)
    ).all()
    return [{"chapter_id": c.id, "chapter_number": fmt_number(c.number), "chapter_title": c.title,
             "series_id": s.id, "series_title": s.title_vi, "last_page_no": p.last_page_no, "mode": p.mode,
             "completed": p.completed, "updated_at": p.updated_at} for p, c, s in rows]


@router.get("/stats")
def my_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    by_status = dict(db.execute(select(UserVocab.status, func.count()).where(UserVocab.user_id == user.id)
                                .group_by(UserVocab.status)).all())
    due = db.execute(select(func.count()).select_from(Flashcard).where(
        Flashcard.user_id == user.id, Flashcard.suspended.is_(False), Flashcard.due_at <= now,
        Flashcard.state != "new")).scalar()
    new = db.execute(select(func.count()).select_from(Flashcard).where(
        Flashcard.user_id == user.id, Flashcard.suspended.is_(False), Flashcard.state == "new")).scalar()
    reviewed_today = db.execute(select(func.count()).select_from(ReviewLog).where(
        ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= day_start)).scalar()
    last30 = db.execute(select(func.count(), func.count().filter(ReviewLog.rating >= 3)).where(
        ReviewLog.user_id == user.id, ReviewLog.reviewed_at >= now - timedelta(days=30))).one()
    days = [d for (d,) in db.execute(
        select(func.date(ReviewLog.reviewed_at)).where(ReviewLog.user_id == user.id)
        .group_by(func.date(ReviewLog.reviewed_at)).order_by(func.date(ReviewLog.reviewed_at).desc())
        .limit(366)).all()]
    streak, cursor = 0, now.date()
    if days and days[0] == cursor - timedelta(days=1):
        cursor = days[0]  # chưa ôn hôm nay nhưng hôm qua có ôn -> chuỗi vẫn còn
    for d in days:
        if d == cursor:
            streak += 1
            cursor -= timedelta(days=1)
        elif d < cursor:
            break
    forecast = []
    for i in range(7):
        start = day_start + timedelta(days=i)
        n = db.execute(select(func.count()).select_from(Flashcard).where(
            Flashcard.user_id == user.id, Flashcard.suspended.is_(False), Flashcard.state != "new",
            Flashcard.due_at < start + timedelta(days=1),
            *( [Flashcard.due_at >= start] if i else [] ))).scalar()
        forecast.append({"date": start.date().isoformat(), "due": n})
    top_lookups = db.execute(select(LookupEvent.term, func.count().label("n")).where(
        LookupEvent.user_id == user.id, LookupEvent.created_at >= now - timedelta(days=30))
        .group_by(LookupEvent.term).order_by(func.count().desc()).limit(10)).all()
    return {
        "vocab": {"total": sum(by_status.values()), **{k: by_status.get(k, 0) for k in ("learning", "known", "ignored")}},
        "cards": {"due_now": due, "new_available": new},
        "reviews": {"today": reviewed_today, "last_30_days": last30[0],
                    "retention_30_days": round(last30[1] / last30[0], 3) if last30[0] else None,
                    "streak_days": streak},
        "forecast_7_days": forecast,
        "top_lookups_30_days": [{"term": t, "count": n} for t, n in top_lookups],
    }
