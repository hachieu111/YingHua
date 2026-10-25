from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.stored_files import StoredFileModel
from app.modules.library.domain.entities import (
    Assets,
    FileContext,
    NewPage,
    Page,
    PageContext,
    Visibility,
)
from app.modules.library.infrastructure.chapter_repository import chapter_entity
from app.modules.library.infrastructure.orm_models import ChapterModel, PageModel, SeriesModel
from app.modules.library.infrastructure.series_repository import series_entity


def _page(m: PageModel, expires_at: datetime | None) -> Page:
    return Page(
        id=m.id,
        chapter_id=m.chapter_id,
        owner_id=m.owner_id,
        page_no=m.page_no,
        created_at=m.created_at,
        original_file_id=m.original_file_id,
        translation_id=m.translation_id,
        width=m.width,
        height=m.height,
        expires_at=expires_at,
    )


def _page_select() -> Select[Any]:
    """Trang kèm hạn lưu của ảnh gốc (chỉ ảnh tải nhanh mới có hạn)."""
    return select(PageModel, StoredFileModel.expires_at).outerjoin(
        StoredFileModel, StoredFileModel.id == PageModel.original_file_id
    )


def _assets(rows: Sequence[Any], extra_files: Sequence[int | None] = ()) -> Assets:
    files = [r[0] for r in rows if r[0] is not None] + [f for f in extra_files if f is not None]
    translations = {r[1] for r in rows if r[1] is not None}
    return Assets(tuple(files), tuple(sorted(translations)))


class SqlPageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, page_id: int) -> Page | None:
        row = (await self._session.execute(_page_select().where(PageModel.id == page_id))).first()
        return _page(row[0], row[1]) if row else None

    async def get_context(self, page_id: int) -> PageContext | None:
        stmt = (
            select(PageModel, StoredFileModel.expires_at, ChapterModel, SeriesModel)
            .outerjoin(StoredFileModel, StoredFileModel.id == PageModel.original_file_id)
            .outerjoin(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .outerjoin(SeriesModel, SeriesModel.id == ChapterModel.series_id)
            .where(PageModel.id == page_id)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        page_model, expires_at, chapter_model, series_model = row
        return PageContext(
            page=_page(page_model, expires_at),
            series=series_entity(series_model) if series_model else None,
            chapter=chapter_entity(chapter_model) if chapter_model else None,
        )

    async def list_for_chapter(self, chapter_id: int) -> list[Page]:
        rows = await self._session.execute(
            _page_select().where(PageModel.chapter_id == chapter_id).order_by(PageModel.page_no)
        )
        return [_page(r[0], r[1]) for r in rows.all()]

    async def lock_chapter_and_next_page_no(self, chapter_id: int) -> int:
        await self._session.execute(
            select(ChapterModel.id).where(ChapterModel.id == chapter_id).with_for_update()
        )
        current = await self._session.scalar(
            select(func.coalesce(func.max(PageModel.page_no), 0)).where(PageModel.chapter_id == chapter_id)
        )
        return int(current or 0) + 1

    async def chapter_has_sha256(self, chapter_id: int, sha256: str) -> bool:
        found = exists().where(
            PageModel.chapter_id == chapter_id,
            PageModel.original_file_id == StoredFileModel.id,
            StoredFileModel.sha256 == sha256,
        )
        return bool(await self._session.scalar(select(found)))

    async def add(self, new_page: NewPage) -> Page:
        model = PageModel(
            chapter_id=new_page.chapter_id,
            owner_id=new_page.owner_id,
            page_no=new_page.page_no,
            original_file_id=new_page.original_file_id,
            translation_id=new_page.translation_id,
            width=new_page.width,
            height=new_page.height,
            created_at=new_page.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _page(model, None)

    async def delete(self, page_id: int) -> None:
        await self._session.execute(delete(PageModel).where(PageModel.id == page_id))

    async def list_quick_uploads(self, owner_id: int, offset: int, limit: int) -> tuple[list[Page], int]:
        conds = [PageModel.owner_id == owner_id, PageModel.chapter_id.is_(None)]
        total = await self._session.scalar(select(func.count()).select_from(PageModel).where(*conds))
        rows = await self._session.execute(
            _page_select()
            .where(*conds)
            .order_by(PageModel.created_at.desc(), PageModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_page(r[0], r[1]) for r in rows.all()], int(total or 0)

    async def page_numbers(self, chapter_id: int) -> list[int]:
        rows = await self._session.execute(
            select(PageModel.page_no).where(PageModel.chapter_id == chapter_id).order_by(PageModel.page_no)
        )
        return list(rows.scalars())

    async def get_by_number(self, chapter_id: int, page_no: int) -> Page | None:
        row = (
            await self._session.execute(
                _page_select().where(PageModel.chapter_id == chapter_id, PageModel.page_no == page_no)
            )
        ).first()
        return _page(row[0], row[1]) if row else None

    async def assets_of_page(self, page_id: int) -> Assets:
        rows = await self._session.execute(
            select(PageModel.original_file_id, PageModel.translation_id).where(PageModel.id == page_id)
        )
        return _assets(rows.all())

    async def assets_of_chapter(self, chapter_id: int) -> Assets:
        rows = await self._session.execute(
            select(PageModel.original_file_id, PageModel.translation_id).where(
                PageModel.chapter_id == chapter_id
            )
        )
        return _assets(rows.all())

    async def assets_of_series(self, series_id: int) -> Assets:
        rows = await self._session.execute(
            select(PageModel.original_file_id, PageModel.translation_id)
            .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .where(ChapterModel.series_id == series_id)
        )
        cover = await self._session.scalar(
            select(SeriesModel.cover_file_id).where(SeriesModel.id == series_id)
        )
        return _assets(rows.all(), [cover])

    async def unreferenced_translation_ids(self, translation_ids: Sequence[int]) -> list[int]:
        if not translation_ids:
            return []
        rows = await self._session.execute(
            select(PageModel.translation_id).where(PageModel.translation_id.in_(list(translation_ids)))
        )
        still_used = set(rows.scalars())
        return [t for t in translation_ids if t not in still_used]

    async def page_ids_for_translation(self, translation_id: int, limit: int) -> list[int]:
        rows = await self._session.execute(
            select(PageModel.id)
            .where(PageModel.translation_id == translation_id)
            .order_by(PageModel.id)
            .limit(limit)
        )
        return list(rows.scalars())

    async def series_ids_of_pages(self, page_ids: Sequence[int]) -> dict[int, int]:
        if not page_ids:
            return {}
        rows = await self._session.execute(
            select(PageModel.id, ChapterModel.series_id)
            .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .where(PageModel.id.in_(list(page_ids)))
        )
        return {page_id: series_id for page_id, series_id in rows.all()}

    async def page_ids_for_series(self, series_id: int) -> list[int]:
        rows = await self._session.execute(
            select(PageModel.id)
            .join(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .where(ChapterModel.series_id == series_id)
        )
        return list(rows.scalars())

    async def list_expired_quick_uploads(self, now: datetime, limit: int) -> list[int]:
        rows = await self._session.execute(
            select(PageModel.id)
            .join(StoredFileModel, StoredFileModel.id == PageModel.original_file_id)
            .where(PageModel.chapter_id.is_(None), StoredFileModel.expires_at <= now)
            .order_by(PageModel.id)
            .limit(limit)
        )
        return list(rows.scalars())

    async def file_contexts(self, file_id: int, translation_ids: Sequence[int]) -> list[FileContext]:
        contexts: list[FileContext] = []
        covers = await self._session.execute(
            select(SeriesModel.visibility, SeriesModel.owner_id).where(SeriesModel.cover_file_id == file_id)
        )
        contexts += [
            FileContext(is_cover=True, series_visibility=Visibility(v), series_owner_id=o)
            for v, o in covers.all()
        ]
        uses_file = PageModel.original_file_id == file_id
        if translation_ids:
            uses_file = or_(uses_file, PageModel.translation_id.in_(list(translation_ids)))
        pages = await self._session.execute(
            select(PageModel.owner_id, SeriesModel.visibility, SeriesModel.owner_id, ChapterModel.is_trial)
            .outerjoin(ChapterModel, ChapterModel.id == PageModel.chapter_id)
            .outerjoin(SeriesModel, SeriesModel.id == ChapterModel.series_id)
            .where(uses_file)
        )
        for page_owner, visibility, series_owner, is_trial in pages.all():
            if visibility is None:
                contexts.append(FileContext(page_owner_id=page_owner))
            else:
                contexts.append(
                    FileContext(
                        series_visibility=Visibility(visibility),
                        series_owner_id=series_owner,
                        chapter_is_trial=bool(is_trial),
                    )
                )
        return contexts
