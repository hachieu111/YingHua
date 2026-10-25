"""Dựng dữ liệu hiển thị cho câu thoại đã lưu (F07.11): pinyin từ bong bóng gốc và trang gốc còn đọc được."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import SavedSentenceItem
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.domain.entities import SavedSentence
from app.modules.vocab.domain.rules import pinyin_of_tokens


async def build_sentence_items(
    uow: VocabUnitOfWork, pages: PageAccessPort, identity: Identity, sentences: Sequence[SavedSentence]
) -> list[SavedSentenceItem]:
    """Kèm pinyin (nếu bong bóng gốc còn) và trang gốc (nếu `identity` còn đọc được trang đó)."""
    bubbles = await uow.bubbles.get_many([s.bubble_id for s in sentences if s.bubble_id is not None])
    page_ids = list({s.page_id for s in sentences if s.page_id is not None})
    readable = {p.page_id: p for p in await pages.describe_pages(identity, page_ids)} if page_ids else {}
    items: list[SavedSentenceItem] = []
    for s in sentences:
        bubble = bubbles.get(s.bubble_id) if s.bubble_id is not None else None
        pinyin = pinyin_of_tokens(bubble.tokens, bubble.pinyin) if bubble else None
        items.append(SavedSentenceItem(s, pinyin, readable.get(s.page_id) if s.page_id is not None else None))
    return items
