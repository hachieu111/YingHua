"""Tra cứu 2 bộ từ điển (đầy đủ / tu tiên) và tách từ bằng jieba.

- Bộ ĐẦY ĐỦ: dict_entries (Thiền Chửu + Trần Văn Chánh) và hanzi (pinyin, bộ thủ, phân rã, nét viết).
- Bộ TU TIÊN: xianxia_entries (VietPhrase/Names/PhienAm). Trả về tách riêng trong khoá "xianxia".
"""

import re
import threading

import jieba
from pypinyin import Style, lazy_pinyin
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models import DictEntry, Hanzi, XianxiaEntry

CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_GLOSS_PREFIX = re.compile(r"^\[[^\]]*\]\s*")
_jieba_lock = threading.Lock()
_jieba_ready = False


def has_cjk(text: str) -> bool:
    return bool(CJK.search(text or ""))


def pinyin_of(text: str) -> str:
    return " ".join(lazy_pinyin(text, style=Style.TONE))


def _ensure_jieba():
    global _jieba_ready
    if not _jieba_ready:
        with _jieba_lock:
            if not _jieba_ready:
                jieba.setLogLevel(60)
                jieba.initialize()
                _jieba_ready = True


def tokenize(text: str) -> list[dict]:
    """[{w, start, end}] chỉ giữ token có chữ Hán."""
    _ensure_jieba()
    return [{"w": w, "start": s, "end": e} for w, s, e in jieba.tokenize(text) if has_cjk(w)]


def entry_ids(db: Session, words: set[str]) -> dict[str, int]:
    if not words:
        return {}
    rows = db.execute(
        select(DictEntry.simplified, func.min(DictEntry.id))
        .where(DictEntry.simplified.in_(words)).group_by(DictEntry.simplified)
    ).all()
    return {w: i for w, i in rows}


def short_gloss(gloss: str, limit: int = 160) -> str:
    g = _GLOSS_PREFIX.sub("", (gloss or "").split("\n")[0]).strip()
    return g if len(g) <= limit else g[:limit].rstrip() + "…"


def _entry_dict(e: DictEntry) -> dict:
    return {
        "id": e.id, "simplified": e.simplified, "traditional": e.traditional,
        "pinyin": e.pinyin, "pinyin_source": e.pinyin_source, "han_viet": e.han_viet,
        "meanings_vi": [m.get("gloss") for m in e.meanings_vi],
        "meanings_en": [m.get("gloss") for m in e.meanings_en],
        "hsk_level": e.hsk_level, "source": e.source,
    }


def han_viet_by_char(db: Session, chars: set[str]) -> dict[str, str]:
    if not chars:
        return {}
    rows = db.execute(
        select(DictEntry.simplified, DictEntry.han_viet)
        .where(DictEntry.simplified.in_(chars), DictEntry.han_viet.is_not(None))
    ).all()
    out: dict[str, str] = {}
    for ch, hv in rows:
        out.setdefault(ch, hv)
    return out


def hanzi_info(db: Session, ch: str, with_strokes: bool = False) -> dict:
    h = db.get(Hanzi, ch)
    hv = han_viet_by_char(db, {ch}).get(ch)
    if h is None:
        return {"ch": ch, "pinyin": pinyin_of(ch) if has_cjk(ch) else None, "han_viet": hv,
                "radical": None, "stroke_count": None, "decomposition": None, "components": [],
                "etymology": None, "definition_en": None, "has_strokes": False,
                **({"stroke_data": None} if with_strokes else {})}
    data = {
        "ch": h.ch, "pinyin": h.pinyin, "pinyin_source": h.pinyin_source, "han_viet": hv,
        "radical": h.radical, "stroke_count": h.stroke_count, "decomposition": h.decomposition,
        "components": h.components or [], "etymology": h.etymology, "definition_en": h.definition_en,
        "has_strokes": h.stroke_data is not None,
    }
    if with_strokes:
        data["stroke_data"] = h.stroke_data
    return data


def xianxia_for(db: Session, term: str) -> dict:
    rows = db.execute(select(XianxiaEntry).where(XianxiaEntry.key == term)).scalars().all()
    by_kind = {r.kind: r for r in rows}
    return {
        "phrase": by_kind["phrase"].meanings if "phrase" in by_kind else [],
        "name": by_kind["name"].meanings if "name" in by_kind else [],
        "char": by_kind["char"].meanings if "char" in by_kind else [],
    }


def lookup(db: Session, term: str) -> dict:
    entries = db.execute(select(DictEntry).where(DictEntry.simplified == term)
                         .order_by(DictEntry.id)).scalars().all()
    chars = [c for c in term if has_cjk(c)]
    hv_map = han_viet_by_char(db, set(chars))
    han_viet = " ".join(hv_map.get(c, "?") for c in chars) if chars else None
    return {
        "term": term,
        "pinyin": pinyin_of(term),
        "han_viet": (entries[0].han_viet if entries and entries[0].han_viet else han_viet),
        "summary": summary_meaning(db, term, entries),
        "entries": [_entry_dict(e) for e in entries],
        "chars": [hanzi_info(db, c) for c in dict.fromkeys(chars)],
        "xianxia": xianxia_for(db, term),
    }


def summary_meaning(db: Session, term: str, entries: list[DictEntry] | None = None) -> str | None:
    """Nghĩa ngắn để hiện trên popup/flashcard: ưu tiên từ điển đầy đủ, sau đó bộ tu tiên."""
    if entries is None:
        entries = db.execute(select(DictEntry).where(DictEntry.simplified == term)
                             .order_by(DictEntry.id)).scalars().all()
    for e in entries:
        for m in e.meanings_vi:
            if m.get("gloss"):
                return short_gloss(m["gloss"])
    xx = xianxia_for(db, term)
    for kind in ("phrase", "name", "char"):
        if xx[kind]:
            return xx[kind][0]
    return None


def segment(db: Session, text: str) -> list[dict]:
    toks = tokenize(text)
    words = {t["w"] for t in toks}
    ids = entry_ids(db, words)
    meanings = {w: summary_meaning(db, w) for w in words}
    return [{**t, "entry_id": ids.get(t["w"]), "pinyin": pinyin_of(t["w"]), "meaning": meanings[t["w"]]}
            for t in toks]


def search(db: Session, q: str, limit: int = 20) -> list[dict]:
    q = q.strip()
    stmt = select(DictEntry)
    if has_cjk(q):
        stmt = stmt.where(DictEntry.simplified.like(f"{q}%"))
    else:
        plain = re.sub(r"[0-9\s]", "", q.lower())
        stmt = stmt.where(or_(
            func.regexp_replace(DictEntry.pinyin_numeric, "[0-9 ]", "", "g").like(f"{plain}%"),
            DictEntry.han_viet.ilike(f"{q}%"),
        ))
    rows = db.execute(stmt.order_by(func.length(DictEntry.simplified), DictEntry.id).limit(limit)).scalars().all()
    return [{"id": e.id, "simplified": e.simplified, "pinyin": e.pinyin, "han_viet": e.han_viet,
             "summary": short_gloss(e.meanings_vi[0]["gloss"]) if e.meanings_vi else None} for e in rows]


def search_xianxia(db: Session, q: str, kind: str | None, limit: int = 20) -> list[dict]:
    stmt = select(XianxiaEntry).where(XianxiaEntry.key.like(f"{q.strip()}%"))
    if kind:
        stmt = stmt.where(XianxiaEntry.kind == kind)
    rows = db.execute(stmt.order_by(func.length(XianxiaEntry.key), XianxiaEntry.id).limit(limit)).scalars().all()
    return [{"id": r.id, "kind": r.kind, "key": r.key, "pinyin": r.pinyin, "meanings": r.meanings} for r in rows]
