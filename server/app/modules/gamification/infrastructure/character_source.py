"""Dữ liệu chữ Hán cho mini-game "Gõ pinyin chém chữ" (F16.01): bộ thủ yếu từ `review_logs`, bộ chữ của ván
từ danh sách HSK (và Sổ tay ở chế độ bộ thủ yếu). SQL thô chỉ ở chỗ cần tách chuỗi thành chữ
(`regexp_split_to_table`) và chọn ngẫu nhiên; luôn dùng tham số bind."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.domain.blade_rules import band_levels
from app.modules.gamification.domain.entities import CharRow, HanziRadicalInfo, WordRow
from app.modules.gamification.domain.minigame_rules import WeakRadical
from app.modules.gamification.infrastructure.foreign_tables import hanzi

RATING_AGAIN, RATING_HARD = 1, 2  # mức Quên, Khó

_WEAK_CHARS = text(
    """
    SELECT t.ch, COUNT(*) AS n
    FROM review_logs l
    JOIN cards c ON c.id = l.card_id
    JOIN vocab_entries v ON v.id = c.vocab_entry_id
    CROSS JOIN LATERAL regexp_split_to_table(v.term, '') AS t(ch)
    WHERE l.user_id = :user_id AND l.rating IN (:again, :hard) AND l.reviewed_at >= :since
    GROUP BY t.ch"""
)
_POOL = """
    pool AS (
        SELECT t.ch FROM vocab_entries v
        CROSS JOIN LATERAL regexp_split_to_table(v.term, '') AS t(ch) WHERE v.user_id = :user_id
        UNION
        SELECT t.ch FROM hsk_words w
        CROSS JOIN LATERAL regexp_split_to_table(w.word, '') AS t(ch) WHERE w.level <= :max_hsk)"""
_RADICAL_CHARS = text(
    f"""
    WITH {_POOL},
    picked AS (
        SELECT h.ch, h.pinyin, h.han_viet FROM hanzi h JOIN pool p ON p.ch = h.ch
        WHERE h.pinyin IS NOT NULL
          AND (COALESCE(h.radical = CAST(:radical AS text), FALSE)
               OR COALESCE(CAST(:radical AS text) = ANY (h.components), FALSE))
        ORDER BY random() LIMIT :limit)
    SELECT x.ch, x.pinyin, x.han_viet,
           (SELECT MIN(w.level) FROM hsk_words w WHERE position(x.ch IN w.word) > 0) AS hsk_level
    FROM picked x"""
)
_RADICAL_WORDS = text(
    """
    SELECT w.word, w.pinyin, w.level
    FROM hsk_words w
    WHERE w.level <= :max_hsk AND char_length(w.word) = 2 AND w.pinyin IS NOT NULL
      AND EXISTS (
          SELECT 1 FROM hanzi h
          WHERE h.ch IN (substr(w.word, 1, 1), substr(w.word, 2, 1))
            AND (COALESCE(h.radical = CAST(:radical AS text), FALSE)
                 OR COALESCE(CAST(:radical AS text) = ANY (h.components), FALSE)))
    ORDER BY random() LIMIT :limit"""
)
_BAND_CHARS = text(
    """
    WITH level_chars AS (
        SELECT t.ch, MIN(w.level) AS lvl FROM hsk_words w
        CROSS JOIN LATERAL regexp_split_to_table(w.word, '') AS t(ch)
        WHERE w.level <= :hi GROUP BY t.ch)
    SELECT h.ch, h.pinyin, h.han_viet, c.lvl
    FROM level_chars c JOIN hanzi h ON h.ch = c.ch
    WHERE h.pinyin IS NOT NULL
    ORDER BY (c.lvl >= :lo) DESC, random() LIMIT :limit"""
)
_BAND_WORDS = text(
    """
    SELECT w.word, w.pinyin, w.level
    FROM hsk_words w
    WHERE w.level BETWEEN :lo AND :hi AND char_length(w.word) = 2 AND w.pinyin IS NOT NULL
    ORDER BY random() LIMIT :limit"""
)
_COMMON_RADICALS = text(
    """
    WITH pool AS (
        SELECT t.ch FROM hsk_words w
        CROSS JOIN LATERAL regexp_split_to_table(w.word, '') AS t(ch) WHERE w.level <= :max_hsk)
    SELECT h.radical, COUNT(*) AS n
    FROM hanzi h JOIN (SELECT DISTINCT ch FROM pool) p ON p.ch = h.ch
    WHERE h.radical IS NOT NULL
    GROUP BY h.radical ORDER BY n DESC, h.radical LIMIT :limit"""
)


def _info(row: Any) -> HanziRadicalInfo:
    return HanziRadicalInfo(str(row[0]), row[1], tuple(row[2] or ()), row[3])


class SqlCharacterSource:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def weak_char_counts(self, user_id: int, since: datetime) -> dict[str, int]:
        rows = await self._session.execute(
            _WEAK_CHARS, {"user_id": user_id, "again": RATING_AGAIN, "hard": RATING_HARD, "since": since}
        )
        return {str(ch): int(n) for ch, n in rows}

    async def hanzi_infos(self, chars: Iterable[str]) -> dict[str, HanziRadicalInfo]:
        wanted = list(dict.fromkeys(chars))
        if not wanted:
            return {}
        rows = await self._session.execute(
            select(hanzi.c.ch, hanzi.c.radical, hanzi.c.components, hanzi.c.pinyin).where(
                hanzi.c.ch.in_(wanted),
                (hanzi.c.radical.is_not(None)) | (hanzi.c.components.is_not(None)),
            )
        )
        return {info.ch: info for info in map(_info, rows)}

    async def band_chars(self, band: int, limit: int) -> list[CharRow]:
        low, high = band_levels(band)
        rows = await self._session.execute(_BAND_CHARS, {"lo": low, "hi": high, "limit": limit})
        return [CharRow(str(r[0]), r[1], r[2], r[3]) for r in rows]

    async def band_words(self, band: int, limit: int) -> list[WordRow]:
        low, high = band_levels(band)
        rows = await self._session.execute(_BAND_WORDS, {"lo": low, "hi": high, "limit": limit})
        return [WordRow(str(r[0]), r[1], r[2]) for r in rows]

    async def radical_chars(self, user_id: int, radical: str, max_hsk: int, limit: int) -> list[CharRow]:
        rows = await self._session.execute(
            _RADICAL_CHARS, {"user_id": user_id, "max_hsk": max_hsk, "radical": radical, "limit": limit}
        )
        return [CharRow(str(r[0]), r[1], r[2], r[3]) for r in rows]

    async def radical_words(self, radical: str, max_hsk: int, limit: int) -> list[WordRow]:
        rows = await self._session.execute(
            _RADICAL_WORDS, {"max_hsk": max_hsk, "radical": radical, "limit": limit}
        )
        return [WordRow(str(r[0]), r[1], r[2]) for r in rows]

    async def common_radicals(self, max_hsk: int, limit: int) -> list[WeakRadical]:
        rows = await self._session.execute(_COMMON_RADICALS, {"max_hsk": max_hsk, "limit": limit})
        return [WeakRadical(str(radical), int(n)) for radical, n in rows]
