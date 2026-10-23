"""Gợi ý từ vựng theo chương (giai đoạn 1: xếp hạng theo luật, chưa dùng LLM).

score = 1.5*log(1+số lần xuất hiện trong chương)
      + 2 nếu user đã tra từ này >= 2 lần (1 nếu tra 1 lần)
      + 3 nếu HSK = trình độ user + 1, +1 nếu HSK = trình độ user
      - 1 nếu là tên riêng (bộ Names tu tiên)
Loại bỏ: từ đã có trong sổ tay, từ user đã bỏ qua / đã nhận ở chương này, HSK thấp hơn trình độ user.
"""

import math
from collections import Counter

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import (Bubble, ChapterVocab, DictEntry, LookupEvent, Page, Translation, User, UserSettings,
                      UserVocab, VocabSuggestion, XianxiaEntry)
from . import dictionary


def rebuild_chapter_vocab(db: Session, chapter_id: int) -> int:
    rows = db.execute(
        select(Bubble).join(Translation, Translation.id == Bubble.translation_id)
        .join(Page, Page.translation_id == Translation.id)
        .where(Page.chapter_id == chapter_id, Translation.status == "done")
        .order_by(Page.page_no, Bubble.idx)
    ).scalars().all()
    counts, first, entry = Counter(), {}, {}
    for b in rows:
        for tk in b.tokens or []:
            w = tk.get("w", "")
            if len(w) < 2 or len(w) > 32:
                continue
            counts[w] += 1
            first.setdefault(w, b.id)
            if tk.get("entry_id"):
                entry[w] = tk["entry_id"]
    db.execute(delete(ChapterVocab).where(ChapterVocab.chapter_id == chapter_id))
    for w, n in counts.items():
        db.add(ChapterVocab(chapter_id=chapter_id, term=w, entry_id=entry.get(w), occurrences=n,
                            first_bubble_id=first[w]))
    db.flush()
    return len(counts)


def generate(db: Session, user: User, chapter_id: int, limit: int = 15) -> list[VocabSuggestion]:
    rebuild_chapter_vocab(db, chapter_id)
    cv = db.execute(select(ChapterVocab).where(ChapterVocab.chapter_id == chapter_id)).scalars().all()
    terms = {c.term for c in cv}
    if not terms:
        db.execute(delete(VocabSuggestion).where(VocabSuggestion.user_id == user.id,
                                                 VocabSuggestion.chapter_id == chapter_id,
                                                 VocabSuggestion.status == "pending"))
        return []

    saved = set(db.execute(select(UserVocab.term).where(UserVocab.user_id == user.id,
                                                        UserVocab.term.in_(terms))).scalars())
    decided = set(db.execute(select(VocabSuggestion.term).where(
        VocabSuggestion.user_id == user.id, VocabSuggestion.chapter_id == chapter_id,
        VocabSuggestion.status != "pending")).scalars())
    lookups = dict(db.execute(select(LookupEvent.term, func.count()).where(
        LookupEvent.user_id == user.id, LookupEvent.term.in_(terms)).group_by(LookupEvent.term)).all())
    names = set(db.execute(select(XianxiaEntry.key).where(XianxiaEntry.kind == "name",
                                                          XianxiaEntry.key.in_(terms))).scalars())
    entry_ids = {c.entry_id for c in cv if c.entry_id}
    hsk = dict(db.execute(select(DictEntry.id, DictEntry.hsk_level).where(DictEntry.id.in_(entry_ids))).all()) \
        if entry_ids else {}
    st = db.get(UserSettings, user.id)
    level = st.hsk_level if st else 1

    scored = []
    for c in cv:
        if c.term in saved or c.term in decided:
            continue
        lvl = hsk.get(c.entry_id)
        if lvl is not None and lvl < level:
            continue
        n_look = lookups.get(c.term, 0)
        score = 1.5 * math.log1p(c.occurrences)
        score += 2 if n_look >= 2 else (1 if n_look == 1 else 0)
        if lvl == level + 1:
            score += 3
        elif lvl == level:
            score += 1
        if c.term in names:
            score -= 1
        if n_look >= 2:
            reason = "looked_up_often"
        elif lvl == level + 1:
            reason = "hsk_next_level"
        elif c.term in names:
            reason = "character_name"
        else:
            reason = "frequent_in_chapter"
        scored.append((round(score, 3), reason, c))
    scored.sort(key=lambda x: (-x[0], x[2].term))

    db.execute(delete(VocabSuggestion).where(VocabSuggestion.user_id == user.id,
                                             VocabSuggestion.chapter_id == chapter_id,
                                             VocabSuggestion.status == "pending"))
    out = []
    for score, reason, c in scored[:limit]:
        s = VocabSuggestion(user_id=user.id, chapter_id=chapter_id, term=c.term, entry_id=c.entry_id,
                            score=score, reason=reason, status="pending")
        db.add(s)
        out.append(s)
    db.flush()
    return out


def suggestion_out(db: Session, s: VocabSuggestion) -> dict:
    cv = db.get(ChapterVocab, (s.chapter_id, s.term))
    return {"id": s.id, "term": s.term, "pinyin": dictionary.pinyin_of(s.term),
            "meaning": dictionary.summary_meaning(db, s.term), "score": s.score, "reason": s.reason,
            "status": s.status, "occurrences": cv.occurrences if cv else None,
            "first_bubble_id": cv.first_bubble_id if cv else None}
