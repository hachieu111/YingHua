"""Sổ tay từ vựng: lưu từ (kèm ngữ cảnh + ảnh cắt bong bóng) và sinh flashcard."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BubbleEdit, Flashcard, StoredFile, User, UserVocab, VocabContext
from . import access, dictionary, storage


def get_own_vocab(db: Session, vocab_id: int, user: User) -> UserVocab:
    v = db.get(UserVocab, vocab_id)
    if v is None or v.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy từ trong sổ tay")
    return v


def ensure_cards(db: Session, v: UserVocab, card_types: list[str]) -> None:
    have = {c.card_type for c in v.flashcards}
    for ct in card_types:
        if ct not in have:
            v.flashcards.append(Flashcard(user_id=v.user_id, card_type=ct,
                                          suspended=v.status != "learning"))


def add_context(db: Session, user: User, v: UserVocab, bubble_id: int) -> VocabContext:
    for c in v.contexts:
        if c.bubble_id == bubble_id:
            return c
    bubble, page = access.get_bubble(db, bubble_id, user)
    if v.term not in bubble.text_zh:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Từ này không có trong bong bóng đã chọn")
    edit = db.get(BubbleEdit, (user.id, bubble.id))

    snippet_id = None
    orig = db.get(StoredFile, page.original_file_id) if page.original_file_id else None
    img = storage.read_image(orig) if orig else None
    if img is not None:
        crop = storage.crop_snippet(img, bubble.x, bubble.y, bubble.w, bubble.h)
        snippet_id = storage.save_image(db, crop, "snippet", fmt=".webp", quality=80, expires_at=None).id

    ctx = VocabContext(bubble_id=bubble.id, page_id=page.id, sentence_zh=bubble.text_zh,
                       sentence_vi=edit.text_vi if edit else bubble.text_vi,
                       snippet_file_id=snippet_id, source_label=access.source_label(page)[:255])
    v.contexts.append(ctx)
    return ctx


def add_vocab(db: Session, user: User, *, term: str, bubble_id: int | None, custom_meaning: str | None,
              note: str | None, source: str, card_types: list[str]) -> tuple[UserVocab, bool]:
    term = term.strip()
    if not dictionary.has_cjk(term):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Từ cần lưu phải có chữ Hán")
    v = db.execute(select(UserVocab).where(UserVocab.user_id == user.id, UserVocab.term == term)
                   ).scalar_one_or_none()
    created = v is None
    if created:
        v = UserVocab(user_id=user.id, term=term, source=source, status="learning",
                      entry_id=dictionary.entry_ids(db, {term}).get(term))
        db.add(v)
        db.flush()
    if custom_meaning is not None:
        v.custom_meaning = custom_meaning
    if note is not None:
        v.note = note
    if bubble_id is not None:
        add_context(db, user, v, bubble_id)
    ensure_cards(db, v, card_types)
    db.flush()
    return v, created


def vocab_out(db: Session, v: UserVocab, detail: bool = False) -> dict:
    meaning = v.custom_meaning or dictionary.summary_meaning(db, v.term)
    data = {
        "id": v.id, "term": v.term, "pinyin": dictionary.pinyin_of(v.term),
        "han_viet": (v.entry.han_viet if v.entry and v.entry.han_viet else None),
        "meaning": meaning, "custom_meaning": v.custom_meaning, "note": v.note,
        "status": v.status, "source": v.source, "entry_id": v.entry_id,
        "created_at": v.created_at, "updated_at": v.updated_at,
        "context_count": len(v.contexts),
        "first_context": context_out(v.contexts[0]) if v.contexts else None,
        "next_due": min((c.due_at for c in v.flashcards if not c.suspended), default=None),
    }
    if detail:
        data["contexts"] = [context_out(c) for c in v.contexts]
        data["flashcards"] = [card_brief(c) for c in v.flashcards]
        data["lookup"] = dictionary.lookup(db, v.term)
    return data


def context_out(c: VocabContext) -> dict:
    return {"id": c.id, "bubble_id": c.bubble_id, "page_id": c.page_id, "sentence_zh": c.sentence_zh,
            "sentence_vi": c.sentence_vi, "source_label": c.source_label,
            "snippet_url": f"/api/vocab/contexts/{c.id}/snippet" if c.snippet_file_id else None,
            "created_at": c.created_at}


def card_brief(c: Flashcard) -> dict:
    return {"id": c.id, "card_type": c.card_type, "state": c.state, "due_at": c.due_at,
            "interval_days": c.interval_days, "ease_factor": c.ease_factor, "reps": c.reps,
            "lapses": c.lapses, "suspended": c.suspended, "last_reviewed_at": c.last_reviewed_at}
