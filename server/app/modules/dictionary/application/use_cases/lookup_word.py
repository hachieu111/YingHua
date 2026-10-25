from __future__ import annotations

import unicodedata
from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.dictionary.application.ports import DictionaryUnitOfWork, PinyinProvider
from app.modules.dictionary.domain.entities import (
    CharacterBreakdown,
    DictEntry,
    Example,
    LookupResult,
    Reading,
)
from app.modules.dictionary.domain.errors import EmptyQueryError, NotChineseTextError, TextTooLongError
from app.modules.dictionary.domain.hsk import resolve_hsk
from app.modules.dictionary.domain.pinyin import has_han, is_han_char
from app.modules.dictionary.domain.specialized import select_specialized

MAX_TERM_LENGTH = 64
GUEST_MAX_DEFINITIONS = 3


def normalize_term(term: str) -> str:
    cleaned = unicodedata.normalize("NFKC", term).strip()
    if not cleaned:
        raise EmptyQueryError()
    if len(cleaned) > MAX_TERM_LENGTH:
        raise TextTooLongError(f"Từ cần tra tối đa {MAX_TERM_LENGTH} ký tự")
    if not has_han(cleaned):
        raise NotChineseTextError()
    return cleaned


def _group_readings(
    entries: list[DictEntry], examples: dict[int, list[Example]], hsk_pos: dict[int, str | None]
) -> list[Reading]:
    """Gộp các mục cùng cách đọc (khác nguồn) thành một Reading; giữ thứ tự xuất hiện."""
    groups: dict[str, list[DictEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.pinyin_numeric.lower(), []).append(entry)
    readings: list[Reading] = []
    for group in groups.values():
        definitions = tuple(d for entry in group for d in entry.definitions)
        english = tuple(dict.fromkeys(e for entry in group for e in entry.english))
        seen: set[str] = set()
        merged_examples: list[Example] = []
        for entry in group:
            for example in examples.get(entry.id, []):
                if example.zh not in seen:
                    seen.add(example.zh)
                    merged_examples.append(example)
        first = group[0]
        readings.append(
            Reading(
                pinyin=first.pinyin,
                pinyin_numeric=first.pinyin_numeric,
                han_viet=next((e.han_viet for e in group if e.han_viet), None),
                part_of_speech=next(
                    (p for e in group for p in (e.part_of_speech, hsk_pos.get(e.id)) if p), None
                ),
                definitions=definitions,
                english=english,
                examples=tuple(merged_examples),
            )
        )
    return readings


class LookupWordUseCase:
    """F06.01 (+ F06.03 nghĩa tu tiên, F06.05 phân rã, F06.08 cấp HSK) — Tra cứu chi tiết một từ (US-NH-26).

    Khách (identity=None) chỉ nhận phần cơ bản: pinyin, vài nghĩa đầu và cấp HSK.
    """

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork], pinyin: PinyinProvider) -> None:
        self._uow_factory = uow_factory
        self._pinyin = pinyin

    async def execute(
        self, term: str, identity: Identity | None, include_specialized: bool = True
    ) -> LookupResult:
        term = normalize_term(term)
        chars = list(dict.fromkeys(c for c in term if is_han_char(c)))
        limited = identity is None
        async with self._uow_factory() as uow:
            entries = await uow.reader.find_entries(term)
            hanzi = await uow.reader.get_hanzi(chars)
            hsk = resolve_hsk(term, await uow.reader.get_hsk_levels([term, *chars]))
            examples = {} if limited else await uow.reader.get_examples([e.id for e in entries])
            specialized = []
            if not limited and include_specialized:
                general = [d.gloss for e in entries for d in e.definitions]
                specialized = select_specialized(await uow.reader.get_specialized(term), general)
            if identity is not None:
                await uow.events.add(identity.user_id, term, entries[0].id if entries else None, "lookup")
                await uow.commit()

        readings = _group_readings(entries, examples, {})
        if limited:
            readings = [
                Reading(r.pinyin, r.pinyin_numeric, None, None, r.definitions[:GUEST_MAX_DEFINITIONS], (), ())
                for r in readings
            ]
        han_viet = next((r.han_viet for r in readings if r.han_viet), None)
        if han_viet is None and not limited and all(hanzi.get(c) and hanzi[c].han_viet for c in chars):
            han_viet = " ".join(hanzi[c].han_viet or "" for c in chars)
        pinyin = readings[0].pinyin if readings else self._pinyin.to_pinyin(term)
        characters = () if limited else tuple(CharacterBreakdown(c, hanzi.get(c)) for c in chars)
        return LookupResult(
            term=term,
            found=bool(entries),
            pinyin=pinyin or None,
            han_viet=han_viet,
            hsk=hsk,
            readings=tuple(readings),
            specialized=tuple(specialized),
            characters=characters,
            limited=limited,
        )
