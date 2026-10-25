"""Dựng dữ liệu hiển thị của sổ tay (kèm thẻ, ngữ cảnh, nguồn truyện) dùng chung cho nhiều use case."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccess, PageAccessPort
from app.modules.vocab.application.dto import ContextSource, ContextView, VocabDetail, VocabListItem
from app.modules.vocab.application.ports import TermDictionary, VocabUnitOfWork
from app.modules.vocab.domain.entities import VocabEntry


async def build_list_items(
    uow: VocabUnitOfWork,
    dictionary: TermDictionary,
    user_id: int,
    entries: Sequence[VocabEntry],
    now: datetime,
) -> list[VocabListItem]:
    """Gắn số ngữ cảnh, ngữ cảnh mới nhất, tóm tắt thẻ, âm Hán Việt bằng truy vấn theo lô (tránh N+1)."""
    ids = [e.id for e in entries]
    contexts = await uow.contexts.summaries(ids)
    srs = await uow.cards.summaries_for_entries(user_id, ids, now)
    sino = await dictionary.sino_vietnamese([e.term for e in entries])
    items: list[VocabListItem] = []
    for entry in entries:
        summary = contexts.get(entry.id)
        items.append(
            VocabListItem(
                entry=entry,
                sino_vietnamese=sino.get(entry.term),
                contexts_count=summary.count if summary else 0,
                first_context=summary.latest if summary else None,
                srs=srs.get(entry.id),
            )
        )
    return items


def _source(page: PageAccess) -> ContextSource:
    return ContextSource(
        series_id=page.series_id,
        series_title=page.series_title,
        chapter_id=page.chapter_id,
        chapter_number=page.chapter_number,
        page_id=page.page_id,
        page_no=page.page_no,
    )


async def build_detail(
    uow: VocabUnitOfWork,
    pages: PageAccessPort,
    dictionary: TermDictionary,
    identity: Identity,
    entry: VocabEntry,
    now: datetime,
) -> VocabDetail:
    """Chi tiết một mục từ: mọi ngữ cảnh (kèm nguồn nếu còn đọc được), ba thẻ, âm Hán Việt."""
    contexts = await uow.contexts.list_for_entry(entry.id)
    page_ids = [c.page_id for c in contexts if c.page_id is not None]
    readable = {p.page_id: p for p in await pages.describe_pages(identity, page_ids)} if page_ids else {}
    views = [
        ContextView(c, _source(readable[c.page_id]) if c.page_id in readable else None) for c in contexts
    ]
    cards = await uow.cards.list_for_entry(entry.user_id, entry.id)
    srs = (await uow.cards.summaries_for_entries(entry.user_id, [entry.id], now)).get(entry.id)
    sino = await dictionary.sino_vietnamese([entry.term])
    return VocabDetail(entry, sino.get(entry.term), views, cards, srs)
