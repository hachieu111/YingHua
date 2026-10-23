"""Nạp các từ điển của module xử lí ảnh vào ptud_db, tách thành 2 bộ riêng.

BỘ 1 — TỪ ĐIỂN ĐẦY ĐỦ (dùng cho đọc, tra cứu, flashcard):
  - từ điển/Tu-dien-ThienChuu-TranVanChanh.yomitan/term_bank_*.json -> dict_entries (source = 'thienchuu')
  - từ điển/từ điển vẽ nét chữ/dictionary.txt                       -> hanzi (pinyin, bộ thủ, phân rã, nghĩa Anh)
  - từ điển/từ điển vẽ nét chữ/graphics.txt                         -> hanzi.stroke_data (thứ tự nét)
  - pinyin còn thiếu: tự sinh bằng pypinyin (pinyin_source = 'pypinyin')

BỘ 2 — TU TIÊN (chỉ cho bộ dịch truyện tu tiên, KHÔNG đưa vào dict_entries/hanzi):
  - từ điển tu tiên/VietPhrase.txt (khoá toàn chữ Hán) -> xianxia_entries (kind = 'phrase')
  - từ điển tu tiên/Names.txt (khoá có chữ Hán)         -> xianxia_entries (kind = 'name')
  - từ điển tu tiên/PhienAm.txt                         -> xianxia_entries (kind = 'char')
  - từ điển tu tiên/LuatNhan.txt                        -> xianxia_rules

Chạy (mật khẩu truyền qua biến môi trường, không ghi vào file):
  DATABASE_URL=postgresql://postgres:<pass>@localhost:5432/ptud_db python scripts/import_dictionaries.py

Script yêu cầu DB trống ở các bảng nó nạp. Muốn nạp lại: chạy với --reset (xoá đúng các bảng này rồi nạp lại).
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values
from pypinyin import Style, lazy_pinyin

ROOT = Path(__file__).resolve().parents[2] / "module xử lí ảnh"
DICT_TV = ROOT / "từ điển"
DICT_TT = ROOT / "từ điển tu tiên"
YOMITAN_DIR = DICT_TV / "Tu-dien-ThienChuu-TranVanChanh.yomitan"
STROKE_DIR = DICT_TV / "từ điển vẽ nét chữ"

MAX_KEY = 32
BATCH = 5000

CJK_CHAR = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
ALL_CJK = re.compile(r"^[㐀-䶿一-鿿豈-﫿]+$")
HAN_VIET_PREFIX = re.compile(r"^\[([^\]]+)\]")
IDS_OPERATORS = set("⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻？?")


def read_lines(path: Path):
    # utf-8-sig để bỏ BOM ở dòng đầu (VietPhrase, Names, PhienAm có BOM)
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line.strip():
                yield line


def pinyin_pair(text: str):
    """Trả về (có dấu, số) hoặc (None, None) nếu pypinyin không đọc được hết các ký tự."""
    tone = lazy_pinyin(text, style=Style.TONE)
    if any(CJK_CHAR.search(syl) for syl in tone):
        return None, None
    numeric = lazy_pinyin(text, style=Style.TONE3, neutral_tone_with_five=True)
    return " ".join(tone), " ".join(numeric)


# ---------------------------------------------------------------- BỘ 1: hanzi
def load_hanzi_rows():
    """dict ch -> row cho bảng hanzi, gộp dictionary.txt + graphics.txt."""
    strokes = {}
    for line in read_lines(STROKE_DIR / "graphics.txt"):
        d = json.loads(line)
        strokes[d["character"]] = {"strokes": d["strokes"], "medians": d["medians"]}

    rows = {}
    for line in read_lines(STROKE_DIR / "dictionary.txt"):
        d = json.loads(line)
        ch = d["character"]
        decomposition = d.get("decomposition") or None
        components = []
        for c in decomposition or "":
            if c in IDS_OPERATORS or c.isascii() or c in components:
                continue
            components.append(c)
        stroke = strokes.get(ch)
        dict_pinyin = " ".join(d.get("pinyin") or []) or None
        rows[ch] = {
            "ch": ch,
            "pinyin": dict_pinyin,
            "pinyin_source": "dictionary" if dict_pinyin else None,
            "radical": d.get("radical"),
            "stroke_count": len(stroke["strokes"]) if stroke else None,
            "decomposition": decomposition,
            "components": components or None,
            "etymology": Json(d["etymology"]) if d.get("etymology") else None,
            "definition_en": d.get("definition"),
            "stroke_data": Json(stroke) if stroke else None,
        }
    for ch, stroke in strokes.items():
        rows.setdefault(ch, {
            "ch": ch, "pinyin": None, "pinyin_source": None, "radical": None,
            "stroke_count": len(stroke["strokes"]), "decomposition": None,
            "components": None, "etymology": None, "definition_en": None,
            "stroke_data": Json(stroke),
        })

    # Chữ không có pinyin trong dictionary.txt: tự sinh bằng pypinyin
    filled = 0
    for ch, row in rows.items():
        if row["pinyin"] is None:
            tone, _ = pinyin_pair(ch)
            if tone:
                row["pinyin"] = tone
                row["pinyin_source"] = "pypinyin"
                filled += 1
    return rows, filled


def upsert_hanzi(cur, hanzi_rows: dict):
    cols = ["ch", "pinyin", "pinyin_source", "radical", "stroke_count", "decomposition",
            "components", "etymology", "definition_en", "stroke_data"]
    values = [tuple(r[c] for c in cols) for r in hanzi_rows.values()]
    execute_values(
        cur,
        f"INSERT INTO hanzi ({', '.join(cols)}) VALUES %s",
        values,
        page_size=BATCH,
    )


# ---------------------------------------------------------------- BỘ 1: dict_entries
def load_thienchuu():
    """Từ điển Thiền Chửu + Trần Văn Chánh. Trả về list dòng cho dict_entries (đã gộp theo khoá)."""
    items = {}
    skipped = Counter()
    for name in ("term_bank_1.json", "term_bank_2.json"):
        for row in json.loads((YOMITAN_DIR / name).read_text(encoding="utf-8")):
            term, gloss = row[0], row[5]
            if not ALL_CJK.match(term) or len(term) > MAX_KEY:
                skipped["not_cjk_or_too_long"] += 1
                continue
            tone, numeric = pinyin_pair(term)
            if tone is None:
                skipped["no_pinyin"] += 1
                continue
            han_viet = None
            if gloss:
                m = HAN_VIET_PREFIX.match(gloss[0])
                han_viet = m.group(1) if m else None
            key = (term, numeric)
            if key in items:
                items[key]["meanings_vi"].extend({"gloss": g, "src": "thienchuu"} for g in gloss)
                continue
            items[key] = {
                "simplified": term,
                "pinyin": tone,
                "pinyin_numeric": numeric,
                "han_viet": han_viet,
                "meanings_vi": [{"gloss": g, "src": "thienchuu"} for g in gloss],
            }
    return list(items.values()), skipped


def upsert_entries(cur, items):
    rows = [(
        i["simplified"], None, i["pinyin"], i["pinyin_numeric"], "pypinyin",
        i["han_viet"], Json(i["meanings_vi"]), Json([]), None, None, "thienchuu",
    ) for i in items]
    execute_values(
        cur,
        """INSERT INTO dict_entries
             (simplified, traditional, pinyin, pinyin_numeric, pinyin_source, han_viet,
              meanings_vi, meanings_en, hsk_level, freq_rank, source)
           VALUES %s""",
        rows,
        page_size=BATCH,
    )


# ---------------------------------------------------------------- BỘ 2: tu tiên
def load_xianxia():
    """Trả về dict (kind, key) -> {'meanings': [...]} cho bảng xianxia_entries."""
    items = {}
    skipped = Counter()

    def add(kind, key, meanings):
        entry = items.setdefault((kind, key), {"meanings": []})
        entry["meanings"].extend(meanings)

    for line in read_lines(DICT_TT / "VietPhrase.txt"):
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not ALL_CJK.match(key) or len(key) > MAX_KEY:
            skipped["phrase:not_cjk_or_too_long"] += 1
            continue
        add("phrase", key, [g.strip() for g in val.split("/") if g.strip()])

    for line in read_lines(DICT_TT / "Names.txt"):
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not CJK_CHAR.search(key) or len(key) > MAX_KEY:
            skipped["name:no_cjk_or_too_long"] += 1
            continue
        add("name", key, [g.strip() for g in val.split("/") if g.strip()])

    for line in read_lines(DICT_TT / "PhienAm.txt"):
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if not key or len(key) > 2:
            skipped["char:bad_key"] += 1
            continue
        add("char", key, [g.strip() for g in val.split("/") if g.strip()])

    return items, skipped


def upsert_xianxia(cur, items: dict):
    rows = []
    no_pinyin = 0
    for (kind, key), entry in items.items():
        tone, numeric = pinyin_pair(key)
        if tone is None:
            no_pinyin += 1
        rows.append((kind, key, tone, numeric, entry["meanings"]))
    execute_values(
        cur,
        """INSERT INTO xianxia_entries (kind, key, pinyin, pinyin_numeric, meanings)
           VALUES %s""",
        rows,
        page_size=BATCH,
    )
    return no_pinyin


def import_rules(cur):
    rules = [l for l in read_lines(DICT_TT / "LuatNhan.txt") if not l.lstrip().startswith("#")]
    execute_values(
        cur,
        "INSERT INTO xianxia_rules (seq, rule) VALUES %s",
        [(i, r) for i, r in enumerate(rules, 1)],
    )
    return len(rules)


# ---------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="xoá dữ liệu do script này nạp rồi nạp lại (không đụng dữ liệu người dùng)")
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("Thiếu biến môi trường DATABASE_URL")

    conn = psycopg2.connect(dsn)
    try:
        with conn, conn.cursor() as cur:
            if args.reset:
                cur.execute("DELETE FROM dict_entries WHERE source = 'thienchuu'")
                cur.execute("DELETE FROM hanzi")
                cur.execute("DELETE FROM xianxia_entries")
                cur.execute("DELETE FROM xianxia_rules")
            else:
                cur.execute("SELECT (SELECT count(*) FROM hanzi) + (SELECT count(*) FROM dict_entries)"
                            " + (SELECT count(*) FROM xianxia_entries) + (SELECT count(*) FROM xianxia_rules)")
                if cur.fetchone()[0]:
                    sys.exit("Các bảng từ điển đã có dữ liệu. Chạy lại với --reset.")

            print("BỘ 1 — từ điển đầy đủ")
            hanzi_rows, filled = load_hanzi_rows()
            upsert_hanzi(cur, hanzi_rows)
            print(f"  hanzi: {len(hanzi_rows)} ký tự; pinyin tự sinh thêm: {filled}")

            items, skipped = load_thienchuu()
            upsert_entries(cur, items)
            print(f"  dict_entries (ThienChuu): {len(items)} từ; bỏ qua: {dict(skipped)}")

            print("BỘ 2 — tu tiên")
            xianxia, skipped2 = load_xianxia()
            no_pinyin = upsert_xianxia(cur, xianxia)
            print(f"  xianxia_entries: {len(xianxia)} mục; không sinh được pinyin: {no_pinyin}; bỏ qua: {dict(skipped2)}")
            print(f"  xianxia_rules: {import_rules(cur)} luật")

            cur.execute("SELECT kind, count(*) FROM xianxia_entries GROUP BY kind ORDER BY kind")
            print("  xianxia theo loại:", cur.fetchall())
        print("Xong, đã commit.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
