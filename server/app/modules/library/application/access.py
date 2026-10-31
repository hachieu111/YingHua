"""Kiểm quyền và dọn dẹp dùng chung cho các use case của M03 (F03.10)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from app.core.errors import PermissionDeniedError, UnauthenticatedError
from app.core.storage import StagedFiles
from app.modules.auth.application.public import Identity
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import (
    Actor,
    Assets,
    Chapter,
    ChapterView,
    PageContext,
    Series,
    SeriesView,
    Visibility,
)
from app.modules.library.domain.errors import (
    ChapterNotFoundError,
    LoginRequiredError,
    PageNotFoundError,
    SeriesNotFoundError,
    VipRequiredError,
)
from app.modules.library.domain.rules import (
    can_edit_series,
    can_read_series,
    is_chapter_locked,
    needs_audit,
    vip_access_level,
)


def actor_of(identity: Identity | None) -> Actor:
    """Đổi danh tính (hoặc Khách) thành người gọi của M03."""
    if identity is None:
        return Actor(user_id=None)
    return Actor(user_id=identity.user_id, is_admin=identity.is_admin)


def require_user(actor: Actor) -> int:
    """Chức năng chỉ dành cho người đã đăng nhập; trả mã người dùng."""
    if actor.user_id is None:
        raise UnauthenticatedError()
    return actor.user_id


async def load_readable_series(uow: LibraryUnitOfWork, series_id: int, actor: Actor) -> Series:
    """Truyện riêng tư của người khác được trả lời như không tồn tại (F03.10)."""
    series = await uow.series.get(series_id)
    if series is None or not can_read_series(series, actor):
        raise SeriesNotFoundError()
    return series


async def load_editable_series(uow: LibraryUnitOfWork, series_id: int, actor: Actor) -> Series:
    series = await load_readable_series(uow, series_id, actor)
    if not can_edit_series(series, actor):
        raise PermissionDeniedError()
    return series


def ensure_chapter_readable(series: Series, chapter: Chapter, actor: Actor) -> None:
    """Khách chỉ đọc chương đọc thử của truyện công khai (F03.03)."""
    if actor.is_guest and not (series.visibility is Visibility.PUBLIC and chapter.is_trial):
        raise LoginRequiredError()


async def ensure_vip_access(
    uow: LibraryUnitOfWork, series: Series, chapter: Chapter, actor: Actor, now: datetime
) -> None:
    """Chương không đọc thử của truyện VIP cần VIP còn hạn, vé đã mở khóa truyện hoặc quyền quản trị (F17.05).

    Chặn cả trang, bong bóng và ảnh trang vì mọi đường đọc đều đi qua đây. Khách đã bị chặn trước đó (401).
    """
    if not series.is_vip or chapter.is_trial or actor.is_admin or actor.user_id is None:
        return
    state = await uow.vip.viewer_state(actor.user_id, [series.id], now)
    if not state.can_read(series.id):
        raise VipRequiredError(details={"series_id": series.id, "has_tickets": state.ticket_balance > 0})


async def load_readable_chapter(
    uow: LibraryUnitOfWork, chapter_id: int, actor: Actor, now: datetime
) -> tuple[Chapter, Series]:
    chapter = await uow.chapters.get(chapter_id)
    if chapter is None:
        raise ChapterNotFoundError()
    series = await load_readable_series(uow, chapter.series_id, actor)
    ensure_chapter_readable(series, chapter, actor)
    await ensure_vip_access(uow, series, chapter, actor, now)
    return chapter, series


async def load_editable_chapter(
    uow: LibraryUnitOfWork, chapter_id: int, actor: Actor
) -> tuple[Chapter, Series]:
    chapter = await uow.chapters.get(chapter_id)
    if chapter is None:
        raise ChapterNotFoundError()
    return chapter, await load_editable_series(uow, chapter.series_id, actor)


async def load_readable_page(
    uow: LibraryUnitOfWork, page_id: int, actor: Actor, now: datetime
) -> PageContext:
    """Trang trong truyện theo quyền đọc truyện; ảnh tải nhanh chỉ chủ ảnh và quản trị viên (F03.08)."""
    ctx = await uow.pages.get_context(page_id)
    if ctx is None:
        raise PageNotFoundError()
    if ctx.series is None or ctx.chapter is None:
        if actor.is_admin or (actor.user_id is not None and ctx.page.owner_id == actor.user_id):
            return ctx
        raise PageNotFoundError()
    if not can_read_series(ctx.series, actor):
        raise PageNotFoundError()
    ensure_chapter_readable(ctx.series, ctx.chapter, actor)
    await ensure_vip_access(uow, ctx.series, ctx.chapter, actor, now)
    return ctx


def can_edit_page(ctx: PageContext, actor: Actor) -> bool:
    if ctx.series is None:
        return actor.is_admin or (actor.user_id is not None and ctx.page.owner_id == actor.user_id)
    return can_edit_series(ctx.series, actor)


async def attach_progress(
    uow: LibraryUnitOfWork, views: list[SeriesView], user_id: int | None
) -> list[SeriesView]:
    """Gắn tiến độ của người gọi vào thẻ truyện bằng một lượt truy vấn theo lô; Khách không có tiến độ."""
    if user_id is None or not views:
        return views
    found = await uow.progress.summaries_for_series(user_id, [v.series.id for v in views])
    return [replace(v, progress=found.get(v.series.id)) for v in views]


async def attach_vip_access(
    uow: LibraryUnitOfWork, views: list[SeriesView], actor: Actor, now: datetime
) -> list[SeriesView]:
    """Gắn quyền truy cập VIP của người gọi vào thẻ truyện bằng một lượt truy vấn theo lô (F17.05).

    Truyện thường luôn là `open`; chỉ hỏi cổng VIP khi có truyện VIP và người gọi đã đăng nhập.
    """
    vip_ids = [v.series.id for v in views if v.series.is_vip]
    if not vip_ids:
        return views
    state = None
    if actor.user_id is not None and not actor.is_admin:
        state = await uow.vip.viewer_state(actor.user_id, vip_ids, now)
    return [
        replace(v, vip_access=vip_access_level(v.series.is_vip, actor, state, v.series.id)) for v in views
    ]


def mark_locked_chapters(chapters: list[ChapterView], view: SeriesView) -> list[ChapterView]:
    """Gắn cờ khóa cho từng chương của truyện VIP theo quyền của người xem (F17.05)."""
    series = view.series
    if not series.is_vip:
        return chapters
    return [
        replace(c, is_locked=is_chapter_locked(True, c.chapter.is_trial, view.vip_access)) for c in chapters
    ]


def mark_editable(views: list[SeriesView], actor: Actor) -> list[SeriesView]:
    """Gắn cờ "được phép sửa" để giao diện quyết định hiển thị nút sửa/xóa (F03.10)."""
    return [replace(v, can_edit=can_edit_series(v.series, actor)) for v in views]


async def record_admin_action(
    uow: LibraryUnitOfWork,
    actor: Actor,
    series: Series,
    action: str,
    target_type: str,
    target_id: int | None,
    now: datetime,
    details: dict[str, Any] | None = None,
) -> None:
    """Ghi nhật ký quản trị khi admin tác động lên nội dung của người khác hoặc truyện chung (F13.06)."""
    if actor.user_id is not None and needs_audit(series, actor):
        await uow.audit.add(actor.user_id, action, target_type, target_id, details or {}, now)


async def purge_assets(uow: LibraryUnitOfWork, staged: StagedFiles, assets: Assets) -> int:
    """Sau khi đã xóa dòng truyện/chương/trang: xóa bản dịch mồ côi và tệp liên quan (F03.09).

    Tệp thật chỉ bị xóa khi giao dịch commit thành công (`staged.finalize`). Trả số tệp đã gỡ khỏi CSDL.
    """
    orphans = await uow.pages.unreferenced_translation_ids(assets.translation_ids)
    derived = await uow.translations.delete_many(orphans)
    keys = await uow.files.delete_many([*assets.file_ids, *derived])
    staged.delete_after_commit(keys)
    return len(keys)
