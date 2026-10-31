from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, exists, false, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.db import escape_like
from app.modules.library.application.ports import SeriesFilter
from app.modules.library.domain.entities import (
    LibraryTab,
    NewSeries,
    Series,
    SeriesStatus,
    SeriesView,
    Visibility,
)
from app.modules.library.infrastructure.orm_models import (
    ChapterModel,
    LibraryItemModel,
    PageModel,
    PageReadModel,
    ReadingProgressModel,
    SeriesModel,
    SeriesRatingModel,
)


def series_entity(m: SeriesModel) -> Series:
    return Series(
        id=m.id,
        owner_id=m.owner_id,
        visibility=Visibility(m.visibility),
        title_vi=m.title_vi,
        status=SeriesStatus(m.status),
        created_at=m.created_at,
        updated_at=m.updated_at,
        title_zh=m.title_zh,
        author=m.author,
        description=m.description,
        cover_file_id=m.cover_file_id,
        est_hsk_level=m.est_hsk_level,
        created_by=m.created_by,
        genres=list(m.genres or []),
        is_vip=m.is_vip,
    )


def _chapter_count(trial_only: bool) -> Any:
    query = select(func.count()).where(ChapterModel.series_id == SeriesModel.id)
    if trial_only:
        query = query.where(ChapterModel.is_trial.is_(True))
    return query.correlate(SeriesModel).scalar_subquery()


def _view_columns(viewer_id: int | None, trial_only: bool) -> list[Any]:
    """Cột số liệu cho thẻ truyện, tính bằng truy vấn con tương quan (không N+1)."""
    rating_avg = (
        select(func.avg(SeriesRatingModel.stars))
        .where(SeriesRatingModel.series_id == SeriesModel.id)
        .correlate(SeriesModel)
        .scalar_subquery()
    )
    rating_count = (
        select(func.count())
        .where(SeriesRatingModel.series_id == SeriesModel.id)
        .correlate(SeriesModel)
        .scalar_subquery()
    )
    if viewer_id is None:
        in_library: Any = literal(False)
        favorite: Any = literal(False)
    else:
        mine = and_(LibraryItemModel.series_id == SeriesModel.id, LibraryItemModel.user_id == viewer_id)
        in_library = exists().where(mine).correlate(SeriesModel)
        favorite = func.coalesce(
            select(LibraryItemModel.is_favorite).where(mine).correlate(SeriesModel).scalar_subquery(),
            false(),
        )
    return [
        _chapter_count(trial_only).label("chapter_count"),
        rating_avg.label("rating_avg"),
        rating_count.label("rating_count"),
        in_library.label("in_library"),
        favorite.label("is_favorite"),
    ]


def _view(row: Any) -> SeriesView:
    return SeriesView(
        series=series_entity(row[0]),
        chapter_count=int(row.chapter_count),
        rating_avg=round(float(row.rating_avg), 2) if row.rating_avg is not None else None,
        rating_count=int(row.rating_count),
        in_library=bool(row.in_library),
        is_favorite=bool(row.is_favorite),
    )


def _pages_in_series() -> Any:
    return (
        select(func.count(PageModel.id))
        .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
        .where(ChapterModel.series_id == SeriesModel.id)
        .correlate(SeriesModel)
        .scalar_subquery()
    )


def _pages_read_in_series(user_id: int) -> Any:
    return (
        select(func.count(PageReadModel.page_id))
        .join(PageModel, PageModel.id == PageReadModel.page_id)
        .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
        .where(ChapterModel.series_id == SeriesModel.id, PageReadModel.user_id == user_id)
        .correlate(SeriesModel)
        .scalar_subquery()
    )


def _tab_condition(tab: LibraryTab, user_id: int) -> ColumnElement[bool] | None:
    finished = and_(_pages_in_series() > 0, _pages_read_in_series(user_id) >= _pages_in_series())
    if tab is LibraryTab.FAVORITES:
        return LibraryItemModel.is_favorite.is_(True)
    if tab is LibraryTab.COMPLETED:
        return finished
    if tab is LibraryTab.READING:
        has_progress = exists().where(
            ReadingProgressModel.user_id == user_id,
            ReadingProgressModel.chapter_id == ChapterModel.id,
            ChapterModel.series_id == SeriesModel.id,
        )
        return and_(has_progress, ~finished)
    return None


def _conditions(flt: SeriesFilter) -> list[ColumnElement[bool]]:
    conds: list[ColumnElement[bool]] = []
    if flt.scope == "public":
        conds.append(SeriesModel.visibility == Visibility.PUBLIC.value)
        if not flt.include_empty:
            has_chapter = exists().where(ChapterModel.series_id == SeriesModel.id)
            if flt.trial_only:
                has_chapter = has_chapter.where(ChapterModel.is_trial.is_(True))
            conds.append(has_chapter)
    elif flt.scope == "mine":
        conds += [SeriesModel.owner_id == flt.viewer_id, SeriesModel.visibility == Visibility.PRIVATE.value]
    elif flt.scope == "library" and flt.viewer_id is not None:
        # Truyện không còn quyền đọc (thành riêng tư của người khác) bị ẩn khỏi Thư viện.
        conds.append(
            or_(SeriesModel.visibility == Visibility.PUBLIC.value, SeriesModel.owner_id == flt.viewer_id)
        )
        tab_cond = _tab_condition(flt.tab, flt.viewer_id)
        if tab_cond is not None:
            conds.append(tab_cond)
    if flt.query:
        like = f"%{escape_like(flt.query)}%"
        conds.append(
            or_(SeriesModel.title_vi.ilike(like, escape="\\"), SeriesModel.title_zh.ilike(like, escape="\\"))
        )
    if flt.hsk is not None:
        conds.append(SeriesModel.est_hsk_level == flt.hsk)
    if flt.hsk_min is not None:
        conds.append(SeriesModel.est_hsk_level >= flt.hsk_min)
    if flt.hsk_max is not None:
        conds.append(SeriesModel.est_hsk_level <= flt.hsk_max)
    if flt.genre:
        conds.append(SeriesModel.genres.contains([flt.genre]))
    return conds


class SqlSeriesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, series_id: int) -> Series | None:
        model = await self._session.get(SeriesModel, series_id)
        return series_entity(model) if model else None

    async def add(self, new_series: NewSeries) -> Series:
        model = SeriesModel(
            owner_id=new_series.owner_id,
            visibility=new_series.visibility.value,
            title_vi=new_series.title_vi,
            title_zh=new_series.title_zh,
            author=new_series.author,
            description=new_series.description,
            status=new_series.status.value,
            est_hsk_level=new_series.est_hsk_level,
            created_by=new_series.created_by,
            genres=list(new_series.genres),
            created_at=new_series.created_at,
            updated_at=new_series.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return series_entity(model)

    async def update(self, series: Series) -> None:
        model = await self._session.get(SeriesModel, series.id)
        if model is None:
            return
        model.owner_id = series.owner_id
        model.visibility = series.visibility.value
        model.title_vi = series.title_vi
        model.title_zh = series.title_zh
        model.author = series.author
        model.description = series.description
        model.cover_file_id = series.cover_file_id
        model.status = series.status.value
        model.est_hsk_level = series.est_hsk_level
        model.created_by = series.created_by
        model.genres = list(series.genres)
        # Truyện đã thành riêng tư thì không còn là truyện VIP (ràng buộc `vip_public`); M17 mới được bật cờ.
        if series.visibility is not Visibility.PUBLIC:
            model.is_vip = False
        await self._session.flush()

    async def delete(self, series_id: int) -> None:
        await self._session.execute(delete(SeriesModel).where(SeriesModel.id == series_id))

    async def owner_has_title(self, owner_id: int, title_vi: str, exclude_id: int | None = None) -> bool:
        conds = [
            SeriesModel.owner_id == owner_id,
            func.lower(SeriesModel.title_vi) == title_vi.lower(),
        ]
        if exclude_id is not None:
            conds.append(SeriesModel.id != exclude_id)
        return bool(await self._session.scalar(select(exists().where(*conds))))

    def _select(self, flt: SeriesFilter) -> Select[Any]:
        stmt = select(SeriesModel, *_view_columns(flt.viewer_id, flt.trial_only))
        if flt.scope == "library" and flt.viewer_id is not None:
            stmt = stmt.join(
                LibraryItemModel,
                and_(LibraryItemModel.series_id == SeriesModel.id, LibraryItemModel.user_id == flt.viewer_id),
            )
        return stmt

    async def search(self, flt: SeriesFilter, offset: int, limit: int) -> tuple[list[SeriesView], int]:
        conds = _conditions(flt)
        count_stmt = select(func.count()).select_from(SeriesModel)
        if flt.scope == "library" and flt.viewer_id is not None:
            count_stmt = count_stmt.join(
                LibraryItemModel,
                and_(LibraryItemModel.series_id == SeriesModel.id, LibraryItemModel.user_id == flt.viewer_id),
            )
        total = await self._session.scalar(count_stmt.where(*conds))
        order: list[Any] = (
            [LibraryItemModel.added_at.desc(), SeriesModel.id.desc()]
            if flt.scope == "library"
            else [SeriesModel.updated_at.desc(), SeriesModel.id.desc()]
        )
        rows = await self._session.execute(
            self._select(flt).where(*conds).order_by(*order).offset(offset).limit(limit)
        )
        return [_view(r) for r in rows.all()], int(total or 0)

    async def get_view(self, series_id: int, viewer_id: int | None, trial_only: bool) -> SeriesView | None:
        stmt = select(SeriesModel, *_view_columns(viewer_id, trial_only)).where(SeriesModel.id == series_id)
        row = (await self._session.execute(stmt)).first()
        return _view(row) if row else None

    async def library_counts(self, series_ids: Sequence[int]) -> dict[int, int]:
        if not series_ids:
            return {}
        rows = await self._session.execute(
            select(LibraryItemModel.series_id, func.count())
            .where(LibraryItemModel.series_id.in_(list(series_ids)))
            .group_by(LibraryItemModel.series_id)
        )
        return {series_id: int(n) for series_id, n in rows.all()}
