"""Kiểm tra quyền xem/sửa truyện, chương, trang, bong bóng."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Bubble, Chapter, Page, Series, User


def can_view(user: User, s: Series) -> bool:
    return s.visibility == "public" or s.owner_id == user.id or user.role == "admin"


def can_edit(user: User, s: Series) -> bool:
    return user.role == "admin" or (s.owner_id is not None and s.owner_id == user.id)


def _deny(edit: bool):
    raise HTTPException(status.HTTP_403_FORBIDDEN,
                        "Bạn không có quyền sửa nội dung này" if edit else "Bạn không có quyền xem nội dung này")


def get_series(db: Session, series_id: int, user: User, edit: bool = False) -> Series:
    s = db.get(Series, series_id)
    if s is None or not can_view(user, s):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy truyện")
    if edit and not can_edit(user, s):
        _deny(True)
    return s


def get_chapter(db: Session, chapter_id: int, user: User, edit: bool = False) -> Chapter:
    c = db.get(Chapter, chapter_id)
    if c is None or not can_view(user, c.series):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy chương")
    if edit and not can_edit(user, c.series):
        _deny(True)
    return c


def get_page(db: Session, page_id: int, user: User, edit: bool = False) -> Page:
    p = db.get(Page, page_id)
    if p is None or not can_view(user, p.chapter.series):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy trang")
    if edit and not can_edit(user, p.chapter.series):
        _deny(True)
    return p


def get_bubble(db: Session, bubble_id: int, user: User) -> tuple[Bubble, Page]:
    """Bong bóng + 1 trang mà user được xem có dùng bản dịch chứa bong bóng đó."""
    b = db.get(Bubble, bubble_id)
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bong bóng")
    pages = db.execute(select(Page).where(Page.translation_id == b.translation_id).order_by(Page.id)).scalars()
    for p in pages:
        if can_view(user, p.chapter.series):
            return b, p
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bong bóng")


def fmt_number(n: Decimal) -> str:
    return str(int(n)) if n == int(n) else str(n.normalize())


def source_label(page: Page) -> str:
    return f"{page.chapter.series.title_vi} – Chương {fmt_number(page.chapter.number)} – Trang {page.page_no}"
