from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, load_editable_chapter, record_admin_action
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import Chapter
from app.modules.library.domain.errors import PublishRequiresAdminError
from app.modules.library.domain.rules import clean_optional_text


class UpdateChapterUseCase:
    """F03.09, F03.05, F03.11 — Sửa số thứ tự, tên chương; quản trị viên bật/tắt cờ đọc thử (US-NH-14)."""

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, chapter_id: int, changes: dict[str, Any]) -> Chapter:
        actor = actor_of(identity)
        if changes.get("is_trial") is not None and not actor.is_admin:
            raise PublishRequiresAdminError()
        now = self._clock.now()
        async with self._uow_factory() as uow:
            chapter, series = await load_editable_chapter(uow, chapter_id, actor)
            if changes.get("number") is not None:
                chapter.number = changes["number"]
            if "title" in changes:
                chapter.title = clean_optional_text(changes["title"], 255)
            if changes.get("is_trial") is not None:
                chapter.is_trial = bool(changes["is_trial"])
            await uow.chapters.update(chapter)
            await record_admin_action(
                uow, actor, series, "chapter.update", "chapter", chapter.id, now, {"fields": sorted(changes)}
            )
            await uow.commit()
        return chapter
