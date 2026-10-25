"""Nạp dữ liệu từ điển cho M06 (chạy được nhiều lần, không sinh trùng).

Nguồn:
  - ptud_db (CSDL cũ): Thiên Chửu (dict_entries), Hán tự (hanzi), từ điển tu tiên (xianxia_*)
  - module xử lí ảnh/từ điển/CVDICT/cvdict_full.json  — CVDICT, CC BY-SA 4.0 (ghi nguồn ph0ngp/CVDICT)
  - module xử lí ảnh/từ điển/HSK/complete.json         — complete-hsk-vocabulary, MIT
  - module xử lí ảnh/từ điển/Tatoeba/*.tsv              — câu ví dụ Tatoeba, CC BY 2.0 FR

Chạy trong thư mục server/:
    python scripts/load_dictionaries.py                 # tất cả các bước, vào yinghua_db
    python scripts/load_dictionaries.py --steps hsk,tatoeba
    python scripts/load_dictionaries.py --reset-xianxia # chép lại từ điển tu tiên
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg
import jieba
from pypinyin import Style, lazy_pinyin
from sqlalchemy import delete, select, text
from sqlalchemy.engine import make_url

from app.container import build_container
from app.core.config import REPO_DIR, get_settings
from app.modules.dictionary.domain.entities import Definition, EntryRow
from app.modules.dictionary.domain.examples import extract_examples
from app.modules.dictionary.domain.pinyin import has_han, is_han_char
from app.modules.dictionary.infrastructure.orm_models import DictEntryModel, DictExampleModel, HskWordModel
from app.modules.dictionary.infrastructure.parsers import parse_cvdict, parse_hsk
from app.modules.dictionary.infrastructure.repositories import SqlDictionaryWriter

DICT_DIR = REPO_DIR / "module xử lí ảnh" / "từ điển"
CVDICT_FILE = DICT_DIR / "CVDICT" / "cvdict_full.json"
HSK_FILE = DICT_DIR / "HSK" / "complete.json"
TATOEBA_DIR = DICT_DIR / "Tatoeba"
STEPS = ("thienchuu", "hanzi", "xianxia", "cvdict", "hsk", "gloss_examples", "tatoeba")
BATCH = 2000
TATOEBA_PER_WORD = 3
TATOEBA_MIN_LEN, TATOEBA_MAX_LEN = 4, 30
UNKNOWN_DIFFICULTY = 8  # từ ngoài HSK được coi là khó hơn HSK 7–9


def log(message: str) -> None:
    print(message, flush=True)


def to_pinyin(textual: str) -> str:
    return " ".join(p.strip() for p in lazy_pinyin(textual, style=Style.TONE) if p.strip())


async def source_connection(target_url: str, source_db: str) -> asyncpg.Connection:
    url = make_url(target_url)
    return await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port or 5432, database=source_db
    )


async def raw_target(session: Any) -> asyncpg.Connection:
    connection = await session.connection()
    raw = await connection.get_raw_connection()
    return raw.driver_connection  # type: ignore[no-any-return]


async def upsert_entries(session: Any, rows: list[EntryRow]) -> tuple[int, int, int]:
    writer = SqlDictionaryWriter(session)
    total = [0, 0, 0]
    for start in range(0, len(rows), BATCH):
        counts = await writer.upsert_entries(rows[start : start + BATCH])
        total = [a + b for a, b in zip(total, counts, strict=True)]
    return total[0], total[1], total[2]


# ------------------------------------------------------------------ bước 1: Thiên Chửu
async def step_thienchuu(session: Any, src: asyncpg.Connection) -> None:
    records = await src.fetch(
        "SELECT simplified, traditional, pinyin, pinyin_numeric, han_viet, meanings_vi, meanings_en "
        "FROM dict_entries WHERE source = 'thienchuu'"
    )
    rows = []
    import json

    for r in records:
        senses = json.loads(r["meanings_vi"]) if isinstance(r["meanings_vi"], str) else r["meanings_vi"]
        english = json.loads(r["meanings_en"]) if isinstance(r["meanings_en"], str) else r["meanings_en"]
        rows.append(
            EntryRow(
                simplified=r["simplified"],
                traditional=r["traditional"],
                pinyin=r["pinyin"],
                pinyin_numeric=r["pinyin_numeric"],
                han_viet=r["han_viet"],
                definitions=tuple(
                    Definition("thienchuu", s["gloss"]) for s in senses or [] if s.get("gloss")
                ),
                english=tuple(str(e) for e in english or []),
                part_of_speech=None,
                source="thienchuu",
            )
        )
    added, updated, skipped = await upsert_entries(session, rows)
    await session.commit()
    log(f"Thiên Chửu: {len(rows)} mục — thêm {added}, cập nhật {updated}, không đổi {skipped}")


# ------------------------------------------------------------------ bước 2: Hán tự (+ âm Hán Việt từ PhienAm)
async def step_hanzi(session: Any, src: asyncpg.Connection) -> None:
    target = await raw_target(session)
    records = await src.fetch(
        "SELECT ch, pinyin, pinyin_source, han_viet, radical, stroke_count, decomposition, components, "
        "etymology::text AS etymology, definition_en, stroke_data::text AS stroke_data FROM hanzi"
    )
    han_viet = {
        r["key"]: r["meanings"][0]
        for r in await src.fetch("SELECT key, meanings FROM xianxia_entries WHERE kind = 'char'")
        if r["meanings"]
    }
    rows = [
        (
            r["ch"],
            r["pinyin"],
            r["pinyin_source"],
            r["han_viet"] or han_viet.get(r["ch"]),
            r["radical"],
            r["stroke_count"],
            r["decomposition"],
            r["components"],
            r["etymology"],
            r["definition_en"],
            r["stroke_data"],
        )
        for r in records
    ]
    await target.executemany(
        """
        INSERT INTO hanzi (ch, pinyin, pinyin_source, han_viet, radical, stroke_count, decomposition,
                           components, etymology, definition_en, stroke_data)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11::jsonb)
        ON CONFLICT (ch) DO UPDATE SET
            pinyin = EXCLUDED.pinyin, pinyin_source = EXCLUDED.pinyin_source, han_viet = EXCLUDED.han_viet,
            radical = EXCLUDED.radical, stroke_count = EXCLUDED.stroke_count,
            decomposition = EXCLUDED.decomposition, components = EXCLUDED.components,
            etymology = EXCLUDED.etymology, definition_en = EXCLUDED.definition_en,
            stroke_data = EXCLUDED.stroke_data
        """,
        rows,
    )
    await session.commit()
    filled = sum(1 for row in rows if row[3])
    log(f"Hán tự: {len(rows)} chữ, {filled} chữ có âm Hán Việt")


# ------------------------------------------------------------------ bước 3: từ điển tu tiên
async def step_xianxia(session: Any, src: asyncpg.Connection, reset: bool) -> None:
    target = await raw_target(session)
    existing = await target.fetchval("SELECT count(*) FROM xianxia_entries")
    if existing and not reset:
        log(f"Tu tiên: đã có {existing} mục — bỏ qua (dùng --reset-xianxia để chép lại)")
        return
    await target.execute("TRUNCATE xianxia_entries, xianxia_rules")
    entries = await src.fetch("SELECT kind, key, pinyin, pinyin_numeric, meanings FROM xianxia_entries")
    await target.copy_records_to_table(
        "xianxia_entries",
        records=[
            (r["kind"], r["key"][:64], r["pinyin"], r["pinyin_numeric"], r["meanings"]) for r in entries
        ],
        columns=["kind", "key", "pinyin", "pinyin_numeric", "meanings"],
    )
    rules = await src.fetch("SELECT seq, rule FROM xianxia_rules")
    await target.copy_records_to_table(
        "xianxia_rules", records=[(r["seq"], r["rule"]) for r in rules], columns=["seq", "rule"]
    )
    await session.commit()
    log(f"Tu tiên: {len(entries)} mục, {len(rules)} luật nhân")


# ------------------------------------------------------------------ bước 4–5: CVDICT, HSK
async def step_cvdict(session: Any) -> None:
    rows = parse_cvdict(CVDICT_FILE.read_bytes())
    added, updated, skipped = await upsert_entries(session, rows)
    await session.commit()
    log(f"CVDICT: {len(rows)} mục — thêm {added}, cập nhật {updated}, không đổi {skipped}")


async def step_hsk(session: Any) -> None:
    rows, rejected = parse_hsk(HSK_FILE.read_bytes())
    writer = SqlDictionaryWriter(session)
    total = [0, 0, 0]
    for start in range(0, len(rows), BATCH):
        counts = await writer.upsert_hsk_words(rows[start : start + BATCH])
        total = [a + b for a, b in zip(total, counts, strict=True)]
    await session.commit()
    levels = collections.Counter(r.level for r in rows)
    log(
        f"HSK 3.0: {len(rows)} từ {dict(sorted(levels.items()))} — thêm {total[0]}, cập nhật {total[1]}; "
        f"bỏ qua {len(rejected)} mục không có cấp HSK 3.0"
    )


# ------------------------------------------------------------------ bước 6: ví dụ trong giải nghĩa Thiên Chửu
async def step_gloss_examples(session: Any) -> None:
    await session.execute(delete(DictExampleModel).where(DictExampleModel.source == "gloss"))
    result = await session.execute(
        select(DictEntryModel.id, DictEntryModel.meanings_vi).where(DictEntryModel.source == "thienchuu")
    )
    rows = []
    for entry_id, senses in result.all():
        for sense in senses or []:
            for zh, vi in extract_examples(str(sense.get("gloss", ""))):
                rows.append(
                    {"entry_id": entry_id, "zh": zh, "pinyin": to_pinyin(zh), "vi": vi, "source": "gloss"}
                )
    for start in range(0, len(rows), BATCH):
        await session.execute(DictExampleModel.__table__.insert(), rows[start : start + BATCH])
    await session.commit()
    log(f"Ví dụ Thiên Chửu: {len(rows)} câu")


# ------------------------------------------------------------------ bước 7: ví dụ đời thường Tatoeba
def read_tsv(name: str) -> Iterable[list[str]]:
    with (TATOEBA_DIR / name).open(encoding="utf-8") as handle:
        for line in handle:
            yield line.rstrip("\n").split("\t")


def traditional_map() -> dict[str, str]:
    """Bảng chữ phồn thể → giản thể suy từ CVDICT (căn chỉnh từng chữ khi hai dạng dài bằng nhau)."""
    import json

    mapping: dict[str, str] = {}
    for simplified, item in json.loads(CVDICT_FILE.read_text(encoding="utf-8")).items():
        trad = str(item.get("trad") or "")
        if len(trad) == len(simplified):
            for t, s in zip(trad, simplified, strict=True):
                if t != s and is_han_char(t) and is_han_char(s):
                    mapping.setdefault(t, s)
    return mapping


async def step_tatoeba(session: Any) -> None:
    started = time.monotonic()
    to_simplified = traditional_map()
    chinese = {
        row[0]: "".join(to_simplified.get(c, c) for c in row[2]) for row in read_tsv("cmn_sentences.tsv")
    }
    vietnamese = {row[0]: row[2] for row in read_tsv("vie_sentences.tsv")}
    translations: dict[str, str] = {}
    for cmn_id, vie_id in read_tsv("cmn-vie_links.tsv"):
        if cmn_id in chinese and vie_id in vietnamese:
            translations.setdefault(cmn_id, vietnamese[vie_id])
    eng_to_vie: dict[str, str] = {}
    for vie_id, eng_id in read_tsv("vie-eng_links.tsv"):
        if vie_id in vietnamese:
            eng_to_vie.setdefault(eng_id, vietnamese[vie_id])
    for cmn_id, eng_id in read_tsv("cmn-eng_links.tsv"):  # nối qua câu tiếng Anh cùng nghĩa
        if cmn_id in chinese and cmn_id not in translations and eng_id in eng_to_vie:
            translations[cmn_id] = eng_to_vie[eng_id]
    log(f"Tatoeba: {len(chinese)} câu Trung, {len(translations)} câu có bản dịch Việt")

    hsk = {w: lv for w, lv in (await session.execute(select(HskWordModel.word, HskWordModel.level))).all()}
    entry_rows = (
        await session.execute(
            text(
                "SELECT DISTINCT ON (simplified) simplified, id FROM dict_entries "
                "ORDER BY simplified, (source = 'cvdict') DESC, id"
            )
        )
    ).all()
    entry_ids = {word: entry_id for word, entry_id in entry_rows}

    jieba.setLogLevel(60)
    candidates: dict[str, list[tuple[bool, int, int, str]]] = collections.defaultdict(list)
    for sentence_id, zh in chinese.items():
        if not TATOEBA_MIN_LEN <= len(zh) <= TATOEBA_MAX_LEN:
            continue
        words = [w for w in jieba.lcut(zh) if has_han(w)]
        if not words:
            continue
        # Độ khó của câu = cấp HSK cao nhất trong câu: câu dễ hiểu được ưu tiên.
        difficulty = max(hsk.get(w, UNKNOWN_DIFFICULTY) for w in words)
        for word in set(words):
            if word in entry_ids:
                candidates[word].append((sentence_id not in translations, difficulty, len(zh), sentence_id))

    await session.execute(delete(DictExampleModel).where(DictExampleModel.source == "tatoeba"))
    rows = []
    for word, options in candidates.items():
        for _, _, _, sentence_id in sorted(options)[:TATOEBA_PER_WORD]:
            zh = chinese[sentence_id]
            rows.append(
                {
                    "entry_id": entry_ids[word],
                    "zh": zh,
                    "pinyin": to_pinyin(zh),
                    "vi": translations.get(sentence_id),
                    "source": "tatoeba",
                    "source_ref": f"tatoeba:{sentence_id}",
                }
            )
    for start in range(0, len(rows), BATCH):
        await session.execute(DictExampleModel.__table__.insert(), rows[start : start + BATCH])
    await session.commit()
    with_vi = sum(1 for r in rows if r["vi"])
    log(
        f"Tatoeba: gắn {len(rows)} câu cho {len(candidates)} từ ({with_vi} câu có bản dịch Việt) "
        f"trong {time.monotonic() - started:.0f} giây"
    )


async def main(steps: list[str], target: str, source_db: str, reset_xianxia: bool) -> None:
    settings = get_settings()
    url = settings.test_database_url if target == "test" else settings.database_url
    if url is None:
        raise SystemExit("Chưa cấu hình TEST_DATABASE_URL")
    container = build_container(settings.model_copy(update={"database_url": url}))
    src = await source_connection(url, source_db) if {"thienchuu", "hanzi", "xianxia"} & set(steps) else None
    try:
        async with container.session_factory() as session:
            for step in steps:
                started = time.monotonic()
                if step == "thienchuu":
                    await step_thienchuu(session, src)  # type: ignore[arg-type]
                elif step == "hanzi":
                    await step_hanzi(session, src)  # type: ignore[arg-type]
                elif step == "xianxia":
                    await step_xianxia(session, src, reset_xianxia)  # type: ignore[arg-type]
                elif step == "cvdict":
                    await step_cvdict(session)
                elif step == "hsk":
                    await step_hsk(session)
                elif step == "gloss_examples":
                    await step_gloss_examples(session)
                elif step == "tatoeba":
                    await step_tatoeba(session)
                log(f"  → xong bước {step} ({time.monotonic() - started:.1f} giây)")
    finally:
        if src is not None:
            await src.close()
        await container.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nạp dữ liệu từ điển YingHua")
    parser.add_argument(
        "--steps", default=",".join(STEPS), help=f"Các bước, phân cách dấu phẩy: {', '.join(STEPS)}"
    )
    parser.add_argument("--target", choices=("main", "test"), default="main")
    parser.add_argument("--source-db", default="ptud_db", help="CSDL cũ chứa Thiên Chửu / Hán tự / tu tiên")
    parser.add_argument("--reset-xianxia", action="store_true")
    args = parser.parse_args()
    chosen = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = set(chosen) - set(STEPS)
    if unknown:
        raise SystemExit(f"Bước không hợp lệ: {', '.join(sorted(unknown))}")
    asyncio.run(main([s for s in STEPS if s in chosen], args.target, args.source_db, args.reset_xianxia))
