"""Nạp mục từ có kiểm quyền cho các use case của M07."""

from __future__ import annotations

from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.domain.entities import VocabEntry
from app.modules.vocab.domain.errors import VocabNotFoundError


async def load_entry(uow: VocabUnitOfWork, user_id: int, entry_id: int) -> VocabEntry:
    """Mục từ của chính người gọi; của người khác được trả lời như không tồn tại (404)."""
    entry = await uow.entries.get(user_id, entry_id)
    if entry is None:
        raise VocabNotFoundError()
    return entry
