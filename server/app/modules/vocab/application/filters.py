"""Dựng bộ lọc sổ tay từ tham số truy vấn, dùng chung cho danh sách (F07.07) và xuất tệp (F07.08)."""

from __future__ import annotations

from datetime import datetime

from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import ListVocabQuery
from app.modules.vocab.domain.entities import VocabFilter
from app.modules.vocab.domain.rules import parse_hsk_filter, parse_status


async def build_vocab_filter(
    pages: PageAccessPort, query: ListVocabQuery, owner_id: int, now: datetime
) -> VocabFilter:
    hsk_level, hsk_none = parse_hsk_filter(query.hsk)
    page_ids = await pages.page_ids_of_series(query.series_id) if query.series_id else None
    return VocabFilter(
        user_id=owner_id,
        status=parse_status(query.status) if query.status else None,
        hsk_level=hsk_level,
        hsk_none=hsk_none,
        query=(query.query or "").strip() or None,
        starred=query.starred,
        page_ids=page_ids,
        due=query.due,
        now=now,
    )
