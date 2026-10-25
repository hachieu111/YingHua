from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, mark_editable, record_admin_action, require_user
from app.modules.library.application.dto import SeriesInput
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import NewSeries, SeriesView, Visibility
from app.modules.library.domain.errors import (
    PublishRequiresAdminError,
    SeriesNotFoundError,
    SeriesTitleDuplicateError,
)
from app.modules.library.domain.rules import (
    clean_genres,
    clean_optional_text,
    clean_title,
    parse_status,
    parse_visibility,
)


class CreateSeriesUseCase:
    """F03.04, F03.05 — Tạo truyện riêng tư (người học) hoặc công khai (quản trị viên) (US-NH-10, US-QT-04).

    Trùng tên với truyện của chính mình: báo xung đột, chỉ tạo khi `confirm_duplicate`.
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, data: SeriesInput) -> SeriesView:
        actor = actor_of(identity)
        user_id = require_user(actor)
        visibility = parse_visibility(data.visibility)
        status = parse_status(data.status)
        if visibility is Visibility.PUBLIC and not actor.is_admin:
            raise PublishRequiresAdminError()
        title = clean_title(data.title_vi)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            owner_id = None if visibility is Visibility.PUBLIC else user_id
            if (
                owner_id is not None
                and not data.confirm_duplicate
                and await uow.series.owner_has_title(owner_id, title)
            ):
                raise SeriesTitleDuplicateError()
            series = await uow.series.add(
                NewSeries(
                    owner_id=owner_id,
                    visibility=visibility,
                    title_vi=title,
                    status=status,
                    created_by=user_id,
                    created_at=now,
                    title_zh=clean_optional_text(data.title_zh, 255),
                    author=clean_optional_text(data.author, 255),
                    description=clean_optional_text(data.description, 5000),
                    est_hsk_level=data.est_hsk_level,
                    genres=clean_genres(data.genres),
                )
            )
            await record_admin_action(uow, actor, series, "series.create", "series", series.id, now)
            view = await uow.series.get_view(series.id, user_id, False)
            if view is None:
                raise SeriesNotFoundError()
            await uow.commit()
        return mark_editable([view], actor)[0]
