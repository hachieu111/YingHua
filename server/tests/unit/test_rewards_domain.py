"""M17 - quy tắc thuần của domain (F17.01, F17.03, F17.04, F17.05, F17.09) và quyền xem tệp chương VIP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.vip_access import ViewerVipState
from app.modules.library.domain.entities import Actor, FileContext, VipAccessLevel, Visibility
from app.modules.library.domain.rules import can_view_file, is_chapter_locked, vip_access_level
from app.modules.rewards.domain.entities import FrameGrant, FrameSource, ItemKind, RewardBundle
from app.modules.rewards.domain.errors import InvalidRewardError
from app.modules.rewards.domain.rules import (
    effective_ai_limit,
    extend_vip,
    validate_bundle,
    validate_item_code,
    validate_item_kind_fields,
    validate_price,
    vip_days_left,
)

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)


def test_extend_vip_stacks_on_remaining_time() -> None:
    """US-NH-94 TC2: còn 2 ngày, cộng 7 ngày thì hạn mới = hạn cũ + 7 ngày (không tính lại từ hôm nay)."""
    current = NOW + timedelta(days=2)
    assert extend_vip(current, 7, NOW) == NOW + timedelta(days=9)


def test_extend_vip_restarts_from_now_when_expired_or_never_had() -> None:
    assert extend_vip(None, 3, NOW) == NOW + timedelta(days=3)
    assert extend_vip(NOW - timedelta(days=5), 3, NOW) == NOW + timedelta(days=3)
    assert extend_vip(NOW, 3, NOW) == NOW + timedelta(days=3)


def test_vip_days_left_rounds_up_and_is_zero_after_expiry() -> None:
    assert vip_days_left(None, NOW) == 0
    assert vip_days_left(NOW, NOW) == 0
    assert vip_days_left(NOW + timedelta(hours=3), NOW) == 1
    assert vip_days_left(NOW + timedelta(days=2, hours=1), NOW) == 3


def test_effective_ai_limit_takes_max_for_vip_and_ignores_lower_vip_limit() -> None:
    """US-NH-95 TC1, TC3: VIP dùng max(hạn mức VIP, hạn mức thường); không VIP luôn dùng hạn mức thường."""
    assert effective_ai_limit(False, 5, 10) == 5
    assert effective_ai_limit(True, 5, 10) == 10
    assert effective_ai_limit(True, 5, 3) == 5


def test_validate_bundle_enforces_per_grant_limits() -> None:
    """F17.01: xu tối đa 100.000, vé 10, ngày VIP 365 mỗi lần."""
    validate_bundle(RewardBundle(coins=100_000, tickets=10, vip_days=365))
    validate_bundle(RewardBundle(coins=-100_000, tickets=-10))
    for bad in (
        RewardBundle(coins=100_001),
        RewardBundle(tickets=11),
        RewardBundle(vip_days=366),
        RewardBundle(vip_days=-1),
        RewardBundle(frame=FrameGrant("sakura_gold", FrameSource.WEEKLY_GOAL, days=0)),
    ):
        with pytest.raises(InvalidRewardError):
            validate_bundle(bad)


def test_item_validation_rules() -> None:
    """F17.09: giá 1-100.000; chỉ trường đúng loại có giá trị; khoảng ngày VIP, vé."""
    assert validate_price(1) == 1 and validate_price(100_000) == 100_000
    for price in (0, 100_001):
        with pytest.raises(InvalidRewardError):
            validate_price(price)
    validate_item_kind_fields(ItemKind.VIP_DAYS, 7, None, None)
    validate_item_kind_fields(ItemKind.VIP_TICKET, None, 3, None)
    validate_item_kind_fields(ItemKind.AVATAR_FRAME, None, None, 4)
    for args in (
        (ItemKind.VIP_DAYS, None, None, None),
        (ItemKind.VIP_DAYS, 7, 1, None),
        (ItemKind.VIP_DAYS, 366, None, None),
        (ItemKind.VIP_TICKET, None, 11, None),
        (ItemKind.AVATAR_FRAME, 7, None, 4),
    ):
        with pytest.raises(InvalidRewardError):
            validate_item_kind_fields(*args)
    assert validate_item_code(" VIP_30D ") == "vip_30d"
    with pytest.raises(InvalidRewardError):
        validate_item_code("Mã Có Dấu")


USER = Actor(user_id=5)
ADMIN = Actor(user_id=1, is_admin=True)
GUEST = Actor(user_id=None)


def test_vip_access_level_for_each_kind_of_viewer() -> None:
    """F17.05: truyện thường luôn mở; quản trị viên đọc hết; VIP thắng vé; còn lại chỉ đọc thử."""
    unlocked = ViewerVipState(False, 1, frozenset({9}))
    assert vip_access_level(False, USER, None, 9) is VipAccessLevel.OPEN
    assert vip_access_level(True, ADMIN, None, 9) is VipAccessLevel.VIP
    assert vip_access_level(True, GUEST, None, 9) is VipAccessLevel.TRIAL_ONLY
    assert vip_access_level(True, USER, ViewerVipState(True, 0, frozenset()), 9) is VipAccessLevel.VIP
    assert vip_access_level(True, USER, unlocked, 9) is VipAccessLevel.UNLOCKED
    assert vip_access_level(True, USER, unlocked, 10) is VipAccessLevel.TRIAL_ONLY
    assert vip_access_level(True, USER, ViewerVipState(), 9) is VipAccessLevel.TRIAL_ONLY


def test_only_non_trial_chapters_of_restricted_viewers_are_locked() -> None:
    assert is_chapter_locked(True, False, VipAccessLevel.TRIAL_ONLY)
    assert not is_chapter_locked(True, True, VipAccessLevel.TRIAL_ONLY)
    assert not is_chapter_locked(True, False, VipAccessLevel.VIP)
    assert not is_chapter_locked(True, False, VipAccessLevel.UNLOCKED)
    assert not is_chapter_locked(False, False, VipAccessLevel.OPEN)


def _vip_page(trial: bool) -> list[FileContext]:
    return [
        FileContext(
            series_visibility=Visibility.PUBLIC,
            chapter_is_trial=trial,
            series_id=9,
            series_is_vip=True,
        )
    ]


def test_vip_chapter_file_needs_vip_unlock_or_admin_but_trial_and_cover_stay_open() -> None:
    """US-NH-96 TC2: không đọc được ảnh chương bị khóa bằng đường dẫn tệp trực tiếp."""
    locked = _vip_page(trial=False)
    assert not can_view_file("original", 9, locked, USER, ViewerVipState())
    assert not can_view_file("original", 9, locked, USER, None)
    assert can_view_file("original", 9, locked, USER, ViewerVipState(is_vip=True))
    assert can_view_file("original", 9, locked, USER, ViewerVipState(unlocked_series_ids=frozenset({9})))
    assert not can_view_file("original", 9, locked, USER, ViewerVipState(unlocked_series_ids=frozenset({3})))
    assert can_view_file("original", 9, locked, ADMIN, None)
    assert not can_view_file("original", 9, locked, GUEST, None)
    assert can_view_file("original", 9, _vip_page(trial=True), USER, ViewerVipState())
    assert can_view_file("original", 9, _vip_page(trial=True), GUEST, None)
    cover = [FileContext(is_cover=True, series_visibility=Visibility.PUBLIC, series_id=9, series_is_vip=True)]
    assert can_view_file("cover", 9, cover, GUEST, None)
