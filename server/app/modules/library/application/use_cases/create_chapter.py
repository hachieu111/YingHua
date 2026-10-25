from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, load_editable_series, record_admin_action
from app.modules.library.application.dto import ChapterInput
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import Chapter
from app.modules.library.domain.errors import PublishRequiresAdminError
from app.modules.library.domain.rules import clean_optional_text


class CreateChapterUseCase:
    """F03.06 — Thêm chương vào truyện của mình (US-NH-11). Cờ đọc thử chỉ quản trị viên được bật (F03.05)."""

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, series_id: int, data: ChapterInput) -> Chapter:
        actor = actor_of(identity)
        if data.is_trial and not actor.is_admin:
            raise PublishRequiresAdminError()
        now = self._clock.now()
        async with self._uow_factory() as uow:
            series = await load_editable_series(uow, series_id, actor)
            chapter = await uow.chapters.add(
                series_id, data.number, clean_optional_text(data.title, 255), data.is_trial, now
            )
            await record_admin_action(uow, actor, series, "chapter.create", "chapter", chapter.id, now)
            await uow.commit()
        return chapter
