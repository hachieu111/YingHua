from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import (
    actor_of,
    load_editable_series,
    mark_editable,
    record_admin_action,
)
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import Series, SeriesView, Visibility
from app.modules.library.domain.errors import PublishRequiresAdminError, SeriesNotFoundError
from app.modules.library.domain.rules import (
    clean_genres,
    clean_optional_text,
    clean_title,
    parse_status,
    parse_visibility,
)


class UpdateSeriesUseCase:
    """F03.09, F03.05, F03.11 — Sửa truyện của mình; quản trị viên sửa bất kỳ truyện và đổi chế độ hiển thị.

    Công khai hóa truyện: bỏ chủ sở hữu (thành thư viện chung). Đưa truyện công khai về riêng tư: chủ là người
    tạo ban đầu, nếu không còn thì là quản trị viên đang thao tác.
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, series_id: int, changes: dict[str, Any]) -> SeriesView:
        actor = actor_of(identity)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            series = await load_editable_series(uow, series_id, actor)
            action = "series.update"
            _apply_fields(series, changes)
            if changes.get("visibility") is not None:
                target = parse_visibility(changes["visibility"])
                if target is not series.visibility:
                    if not actor.is_admin:
                        raise PublishRequiresAdminError()
                    _change_visibility(series, target, actor.user_id)
                    action = "series.visibility"
            await uow.series.update(series)
            await record_admin_action(
                uow, actor, series, action, "series", series.id, now, {"fields": sorted(changes)}
            )
            view = await uow.series.get_view(series.id, actor.user_id, False)
            if view is None:
                raise SeriesNotFoundError()
            await uow.commit()
        return mark_editable([view], actor)[0]


def _apply_fields(series: Series, changes: dict[str, Any]) -> None:
    if "title_vi" in changes:
        series.title_vi = clean_title(changes["title_vi"])
    if "title_zh" in changes:
        series.title_zh = clean_optional_text(changes["title_zh"], 255)
    if "author" in changes:
        series.author = clean_optional_text(changes["author"], 255)
    if "description" in changes:
        series.description = clean_optional_text(changes["description"], 5000)
    if "est_hsk_level" in changes:
        series.est_hsk_level = changes["est_hsk_level"]
    if "genres" in changes:
        series.genres = list(clean_genres(changes["genres"]))
    if changes.get("status") is not None:
        series.status = parse_status(changes["status"])


def _change_visibility(series: Series, target: Visibility, admin_id: int | None) -> None:
    series.visibility = target
    if target is Visibility.PUBLIC:
        if series.created_by is None:
            series.created_by = series.owner_id
        series.owner_id = None
    else:
        series.owner_id = series.created_by or admin_id
