"""M03 — quy tắc quyền, tiến độ, thể loại, quyền xem tệp (F03.10, F03.12, F03.03)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.errors import InvalidInputError
from app.modules.library.domain.entities import (
    Actor,
    FileContext,
    Series,
    SeriesStatus,
    Visibility,
)
from app.modules.library.domain.errors import InvalidGenreError, InvalidRatingError, SeriesTitleRequiredError
from app.modules.library.domain.rules import (
    can_edit_series,
    can_read_series,
    can_view_file,
    clean_genres,
    clean_title,
    nearest_page_no,
    needs_audit,
    parse_status,
    validate_stars,
)

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def _series(visibility: Visibility, owner_id: int | None) -> Series:
    return Series(
        id=1,
        owner_id=owner_id,
        visibility=visibility,
        title_vi="Truyện",
        status=SeriesStatus.ONGOING,
        created_at=NOW,
        updated_at=NOW,
    )


GUEST = Actor(user_id=None)
OWNER = Actor(user_id=5)
OTHER = Actor(user_id=6)
ADMIN = Actor(user_id=1, is_admin=True)


def test_private_series_is_hidden_from_others_but_visible_to_owner_and_admin() -> None:
    """US-NH-15: truyện riêng tư của người khác không tồn tại với người ngoài."""
    private = _series(Visibility.PRIVATE, 5)
    assert can_read_series(private, OWNER)
    assert can_read_series(private, ADMIN)
    assert not can_read_series(private, OTHER)
    assert not can_read_series(private, GUEST)


def test_public_series_is_readable_by_everyone_but_editable_only_by_admin() -> None:
    public = _series(Visibility.PUBLIC, None)
    assert can_read_series(public, GUEST)
    assert not can_edit_series(public, OTHER)
    assert can_edit_series(public, ADMIN)


def test_owner_can_edit_own_private_series() -> None:
    private = _series(Visibility.PRIVATE, 5)
    assert can_edit_series(private, OWNER)
    assert not can_edit_series(private, OTHER)


def test_admin_actions_on_others_content_are_audited() -> None:
    assert needs_audit(_series(Visibility.PUBLIC, None), ADMIN)
    assert needs_audit(_series(Visibility.PRIVATE, 5), ADMIN)
    assert not needs_audit(_series(Visibility.PRIVATE, 1), ADMIN)
    assert not needs_audit(_series(Visibility.PRIVATE, 5), OWNER)


@pytest.mark.parametrize(
    ("pages", "target", "expected"),
    [([1, 2, 4, 5], 3, 2), ([1, 5], 4, 5), ([2], 9, 2), ([], 1, None), ([1, 3], 2, 1)],
)
def test_nearest_page_prefers_closest_then_earlier(
    pages: list[int], target: int, expected: int | None
) -> None:
    """F03.12: trang đã xóa → chuyển tới trang gần nhất còn tồn tại."""
    assert nearest_page_no(pages, target) == expected


def test_clean_genres_dedupes_and_limits() -> None:
    assert clean_genres(["Hành động", " hành  động ", "", "Tình cảm"]) == ("Hành động", "Tình cảm")
    with pytest.raises(InvalidGenreError):
        clean_genres([f"g{i}" for i in range(9)])
    with pytest.raises(InvalidGenreError):
        clean_genres(["x" * 33])


def test_title_is_required_and_whitespace_collapsed() -> None:
    assert clean_title("  Truyện   hay ") == "Truyện hay"
    with pytest.raises(SeriesTitleRequiredError):
        clean_title("   ")


@pytest.mark.parametrize("stars", [0, 6, -1])
def test_stars_outside_1_to_5_are_rejected(stars: int) -> None:
    with pytest.raises(InvalidRatingError):
        validate_stars(stars)


def test_invalid_series_status_is_rejected() -> None:
    with pytest.raises(InvalidInputError):
        parse_status("archived")


def test_guest_sees_only_trial_chapters_but_any_cover_of_public_series() -> None:
    """F03.03: Khách chỉ xem ảnh chương đọc thử của truyện công khai."""
    trial = [FileContext(series_visibility=Visibility.PUBLIC, chapter_is_trial=True)]
    normal = [FileContext(series_visibility=Visibility.PUBLIC, chapter_is_trial=False)]
    cover = [FileContext(is_cover=True, series_visibility=Visibility.PUBLIC)]
    assert can_view_file("original", 9, trial, GUEST)
    assert not can_view_file("original", 9, normal, GUEST)
    assert can_view_file("original", 9, normal, OTHER)
    assert can_view_file("cover", 9, cover, GUEST)


def test_private_and_quick_upload_files_belong_to_their_owner() -> None:
    private = [FileContext(series_visibility=Visibility.PRIVATE, series_owner_id=5, chapter_is_trial=False)]
    quick = [FileContext(page_owner_id=5)]
    assert can_view_file("original", 5, private, OWNER)
    assert not can_view_file("original", 5, private, OTHER)
    assert can_view_file("original", 5, quick, OWNER)
    assert not can_view_file("original", 5, quick, OTHER)
    assert can_view_file("original", 5, quick, ADMIN)


def test_avatar_needs_login_and_snippet_is_owner_only() -> None:
    assert can_view_file("avatar", 5, [], OTHER)
    assert not can_view_file("avatar", 5, [], GUEST)
    assert not can_view_file("snippet", 5, [], OTHER)
    assert can_view_file("snippet", 5, [], OWNER)
    # security.md: quản trị viên xem được mọi dữ liệu, kể cả ảnh ngữ cảnh của sổ tay (F13.07).
    assert can_view_file("snippet", 5, [], ADMIN)
