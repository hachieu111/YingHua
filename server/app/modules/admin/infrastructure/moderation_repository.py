from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.application.dto import ModerationTarget, PersonRef, RemovalItem, UploadItem
from app.modules.admin.domain.moderation import MAX_PAGE_SIDE_PX, MIN_PAGE_SIDE_PX, moderation_flags
from app.modules.admin.infrastructure import foreign_tables as ft
from app.modules.admin.infrastructure.orm_models import ContentRemovalModel


def _person(user_id: int | None, name: str | None, email: str | None) -> PersonRef | None:
    return None if user_id is None else PersonRef(user_id, name or "", email or "")


class SqlModerationRepository:
    """Kiểm duyệt ảnh (F13.04). Chỉ đánh dấu `removed_at`; nơi phục vụ tệp đã tôn trọng cờ này."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_uploads(
        self, auto_flags: bool, flagged_only: bool, offset: int, limit: int
    ) -> tuple[list[UploadItem], int]:
        f, p, t, u = ft.stored_files, ft.pages, ft.translations, ft.users
        twin = ft.stored_files.alias("twin")
        duplicates = (
            select(func.count())
            .select_from(twin)
            .where(
                twin.c.sha256 == f.c.sha256,
                twin.c.kind == "original",
                twin.c.removed_at.is_(None),
                twin.c.id != f.c.id,
            )
            .correlate(f)
            .scalar_subquery()
        )
        source = (
            f.outerjoin(p, p.c.original_file_id == f.c.id)
            .outerjoin(t, t.c.id == p.c.translation_id)
            .outerjoin(u, u.c.id == f.c.owner_id)
        )
        conditions: list[Any] = [f.c.kind == "original", f.c.removed_at.is_(None)]
        if flagged_only:
            suspicious_size = and_(
                f.c.width.is_not(None),
                f.c.height.is_not(None),
                or_(
                    func.least(f.c.width, f.c.height) < MIN_PAGE_SIDE_PX,
                    func.greatest(f.c.width, f.c.height) > MAX_PAGE_SIDE_PX,
                ),
            )
            conditions.append(or_(suspicious_size, duplicates > 0, t.c.status == "failed"))
        total = await self._session.scalar(select(func.count()).select_from(source).where(*conditions))
        rows = await self._session.execute(
            select(
                f.c.id,
                f.c.mime_type,
                f.c.size_bytes,
                f.c.width,
                f.c.height,
                f.c.created_at,
                p.c.id.label("page_id"),
                p.c.chapter_id,
                t.c.status,
                u.c.id.label("user_id"),
                u.c.display_name,
                u.c.email,
                duplicates.label("duplicates"),
            )
            .select_from(source)
            .where(*conditions)
            .order_by(f.c.created_at.desc(), f.c.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = [
            UploadItem(
                file_id=r.id,
                page_id=r.page_id,
                mime_type=r.mime_type,
                size_bytes=r.size_bytes,
                width=r.width,
                height=r.height,
                uploaded_at=r.created_at,
                uploader=_person(r.user_id, r.display_name, r.email),
                flags=moderation_flags(r.width, r.height, r.duplicates, r.status == "failed")
                if auto_flags
                else [],
                quick_upload=r.page_id is not None and r.chapter_id is None,
            )
            for r in rows.all()
        ]
        return items, int(total or 0)

    async def resolve_target(self, page_id: int | None, file_id: int | None) -> ModerationTarget | None:
        p = ft.pages
        if page_id is not None:
            page = (
                await self._session.execute(select(p.c.original_file_id).where(p.c.id == page_id))
            ).first()
            if page is None or page.original_file_id is None:
                return None
            root = int(page.original_file_id)
        elif file_id is not None:
            root = file_id
        else:
            return None
        owner_row = (
            await self._session.execute(
                select(ft.stored_files.c.owner_id).where(ft.stored_files.c.id == root)
            )
        ).first()
        if owner_row is None:
            return None
        return ModerationTarget(
            root_file_id=root,
            page_id=page_id,
            owner_id=owner_row.owner_id,
            file_ids=await self._related_file_ids(root),
        )

    async def _related_file_ids(self, root: int) -> list[int]:
        """Ảnh gốc + ảnh dẫn xuất (đã xóa chữ, đã dịch) + ảnh ngữ cảnh đã cắt từ trang dùng ảnh này."""
        p, t = ft.pages, ft.translations
        pages_of_root = (
            await self._session.execute(
                select(p.c.id, p.c.translation_id).where(p.c.original_file_id == root)
            )
        ).all()
        page_ids = [int(r.id) for r in pages_of_root]
        translation_ids = {int(r.translation_id) for r in pages_of_root if r.translation_id is not None}
        derived = await self._session.execute(
            select(t.c.inpainted_file_id, t.c.rendered_file_id).where(
                or_(t.c.id.in_(translation_ids), t.c.source_file_id == root)
            )
        )
        file_ids = {root}
        for inpainted, rendered in derived.all():
            file_ids.update(int(x) for x in (inpainted, rendered) if x is not None)
        if page_ids:
            snippets = await self._session.execute(
                select(ft.vocab_contexts.c.snippet_file_id).where(
                    ft.vocab_contexts.c.page_id.in_(page_ids),
                    ft.vocab_contexts.c.snippet_file_id.is_not(None),
                )
            )
            file_ids.update(int(x) for (x,) in snippets.all())
        return sorted(file_ids)

    async def mark_removed(self, file_ids: list[int], at: datetime) -> list[int]:
        f = ft.stored_files
        rows = await self._session.execute(
            update(f)
            .where(f.c.id.in_(file_ids), f.c.removed_at.is_(None))
            .values(removed_at=at)
            .returning(f.c.id)
        )
        return [int(x) for (x,) in rows.all()]

    async def add_removal(
        self, file_id: int | None, page_id: int | None, reason: str, removed_by: int, at: datetime
    ) -> int:
        model = ContentRemovalModel(
            file_id=file_id, page_id=page_id, reason=reason, removed_by=removed_by, created_at=at
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get_removal(self, removal_id: int) -> RemovalItem:
        items, _ = await self._removals(ContentRemovalModel.id == removal_id, 0, 1)
        return items[0]

    async def list_removals(self, offset: int, limit: int) -> tuple[list[RemovalItem], int]:
        return await self._removals(None, offset, limit)

    async def _removals(self, condition: Any, offset: int, limit: int) -> tuple[list[RemovalItem], int]:
        c = ContentRemovalModel
        remover, owner = ft.users.alias("remover"), ft.users.alias("owner")
        query = (
            select(
                c,
                remover.c.display_name.label("remover_name"),
                remover.c.email.label("remover_email"),
                ft.stored_files.c.owner_id,
                owner.c.display_name.label("owner_name"),
                owner.c.email.label("owner_email"),
            )
            .outerjoin(remover, remover.c.id == c.removed_by)
            .outerjoin(ft.stored_files, ft.stored_files.c.id == c.file_id)
            .outerjoin(owner, owner.c.id == ft.stored_files.c.owner_id)
        )
        count = select(func.count()).select_from(c)
        if condition is not None:
            query, count = query.where(condition), count.where(condition)
        total = await self._session.scalar(count)
        rows = await self._session.execute(query.order_by(c.id.desc()).offset(offset).limit(limit))
        items = [
            RemovalItem(
                id=r.ContentRemovalModel.id,
                file_id=r.ContentRemovalModel.file_id,
                page_id=r.ContentRemovalModel.page_id,
                reason=r.ContentRemovalModel.reason,
                removed_at=r.ContentRemovalModel.created_at,
                removed_by=_person(r.ContentRemovalModel.removed_by, r.remover_name, r.remover_email),
                owner=_person(r.owner_id, r.owner_name, r.owner_email),
            )
            for r in rows.all()
        ]
        return items, int(total or 0)
