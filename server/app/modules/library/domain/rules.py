"""Quy tắc nghiệp vụ thuần của M03 (F03.10 quyền sở hữu, F03.12 trang gần nhất, kiểm tra dữ liệu)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.core.errors import InvalidInputError
from app.core.vip_access import ViewerVipState
from app.modules.library.domain.entities import (
    Actor,
    FileContext,
    ReadingMode,
    Series,
    SeriesStatus,
    VipAccessLevel,
    Visibility,
)
from app.modules.library.domain.errors import (
    InvalidGenreError,
    InvalidRatingError,
    SeriesTitleRequiredError,
)

TITLE_MAX_LENGTH = 255
GENRE_MAX_LENGTH = 32
MAX_GENRES = 8
MAX_FILES_PER_UPLOAD = 20
MIN_STARS = 1
MAX_STARS = 5
# Loại tệp chỉ chủ sở hữu và quản trị viên xem được, kể cả khi truyện công khai.
_PRIVATE_KINDS = frozenset({"snippet"})
_LOGIN_ONLY_KINDS = frozenset({"avatar", "audio"})


def can_read_series(series: Series, actor: Actor) -> bool:
    """Đọc: truyện công khai, hoặc chủ sở hữu, hoặc quản trị viên (F03.10)."""
    if series.visibility is Visibility.PUBLIC:
        return True
    return actor.is_admin or (actor.user_id is not None and series.owner_id == actor.user_id)


def can_edit_series(series: Series, actor: Actor) -> bool:
    """Sửa/xóa: chủ sở hữu hoặc quản trị viên. Truyện công khai không có chủ nên chỉ admin sửa được."""
    if actor.is_admin:
        return True
    return actor.user_id is not None and series.owner_id == actor.user_id


def needs_audit(series: Series, actor: Actor) -> bool:
    """Quản trị viên tác động lên nội dung không phải của mình thì ghi nhật ký (F13.06)."""
    return actor.is_admin and series.owner_id != actor.user_id


def clean_title(raw: str | None) -> str:
    title = " ".join((raw or "").split())
    if not title:
        raise SeriesTitleRequiredError()
    if len(title) > TITLE_MAX_LENGTH:
        raise SeriesTitleRequiredError(f"Tên truyện tối đa {TITLE_MAX_LENGTH} ký tự")
    return title


def clean_optional_text(raw: str | None, max_length: int) -> str | None:
    value = (raw or "").strip()
    return value[:max_length] if value else None


def clean_genres(raw: Iterable[str] | None) -> tuple[str, ...]:
    """Chuẩn hóa thể loại: bỏ trống/trùng (không phân biệt hoa thường), giới hạn số lượng và độ dài."""
    seen: dict[str, str] = {}
    for item in raw or ():
        genre = " ".join(item.split())
        if not genre:
            continue
        if len(genre) > GENRE_MAX_LENGTH:
            raise InvalidGenreError(f"Thể loại tối đa {GENRE_MAX_LENGTH} ký tự")
        seen.setdefault(genre.casefold(), genre)
    if len(seen) > MAX_GENRES:
        raise InvalidGenreError(f"Tối đa {MAX_GENRES} thể loại")
    return tuple(seen.values())


def parse_visibility(value: str) -> Visibility:
    try:
        return Visibility(value)
    except ValueError as exc:
        raise InvalidInputError("Chế độ hiển thị không hợp lệ") from exc


def parse_status(value: str) -> SeriesStatus:
    try:
        return SeriesStatus(value)
    except ValueError as exc:
        raise InvalidInputError("Trạng thái truyện không hợp lệ") from exc


def parse_mode(value: str) -> ReadingMode:
    try:
        return ReadingMode(value)
    except ValueError as exc:
        raise InvalidInputError("Chế độ đọc không hợp lệ") from exc


def validate_stars(stars: int) -> int:
    if not MIN_STARS <= stars <= MAX_STARS:
        raise InvalidRatingError()
    return stars


def nearest_page_no(page_nos: Sequence[int], target: int) -> int | None:
    """Trang còn tồn tại gần `target` nhất (hòa lấy trang đứng trước); None nếu hết trang (F03.12)."""
    if not page_nos:
        return None
    return min(page_nos, key=lambda n: (abs(n - target), n))


def vip_access_level(
    is_vip_series: bool, actor: Actor, state: ViewerVipState | None, series_id: int
) -> VipAccessLevel:
    """Quyền truy cập của người xem với một truyện (F17.05).

    Quản trị viên đọc mọi chương dù không VIP; đang VIP thắng việc đã mở khóa bằng vé; Khách chỉ đọc thử.
    """
    if not is_vip_series:
        return VipAccessLevel.OPEN
    if actor.is_admin:
        return VipAccessLevel.VIP
    if state is None:
        return VipAccessLevel.TRIAL_ONLY
    if state.is_vip:
        return VipAccessLevel.VIP
    if series_id in state.unlocked_series_ids:
        return VipAccessLevel.UNLOCKED
    return VipAccessLevel.TRIAL_ONLY


def is_chapter_locked(is_vip_series: bool, is_trial: bool, level: VipAccessLevel) -> bool:
    """Chương bị khóa với người xem: truyện VIP, không phải chương đọc thử, người xem chưa có quyền."""
    return is_vip_series and not is_trial and level is VipAccessLevel.TRIAL_ONLY


def can_view_file(
    kind: str,
    file_owner_id: int | None,
    contexts: Sequence[FileContext],
    actor: Actor,
    vip: ViewerVipState | None = None,
) -> bool:
    """Quyền xem một tệp theo nơi nó được dùng (F03.10, F03.03, F01.10, F17.05).

    `vip` là quyền VIP của người xem với các truyện VIP chứa tệp; None nghĩa là không có quyền (Khách)."""
    # Quản trị viên xem được mọi tệp, kể cả ảnh ngữ cảnh của sổ tay (security.md, F13.07).
    if actor.is_admin:
        return True
    if actor.user_id is not None and file_owner_id == actor.user_id:
        return True
    if kind in _PRIVATE_KINDS:
        return False
    if kind in _LOGIN_ONLY_KINDS:
        return not actor.is_guest
    return any(_context_allows(ctx, actor, vip) for ctx in contexts)


def _context_allows(ctx: FileContext, actor: Actor, vip: ViewerVipState | None) -> bool:
    if ctx.series_visibility is None:  # ảnh tải nhanh: chỉ chủ ảnh
        return actor.user_id is not None and ctx.page_owner_id == actor.user_id
    if ctx.series_visibility is Visibility.PRIVATE:
        return actor.user_id is not None and ctx.series_owner_id == actor.user_id
    if ctx.is_cover:
        return True
    if actor.is_guest:
        return bool(ctx.chapter_is_trial)  # Khách chỉ xem chương đọc thử (F03.03)
    if ctx.series_is_vip and not ctx.chapter_is_trial:
        # Ảnh chương VIP: không đọc được bằng đường dẫn tệp trực tiếp nếu chưa có quyền (F17.05).
        return vip is not None and ctx.series_id is not None and vip.can_read(ctx.series_id)
    return True
