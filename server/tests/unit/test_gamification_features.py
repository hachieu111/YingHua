"""M16 - Đeo huy hiệu, bộ thủ yếu, bảng xếp hạng ẩn danh (F16.01, F16.07, F16.08, F16.12)."""

from __future__ import annotations

import pytest

from app.core.learning_events import LearningSignal, LearningSource
from app.modules.auth.application.public import Identity, Role
from app.modules.gamification.application.dto import LeaderboardEntry, Notice
from app.modules.gamification.application.use_cases.equip_achievement import EquipAchievementUseCase
from app.modules.gamification.application.use_cases.get_leaderboard import GetLeaderboardUseCase
from app.modules.gamification.application.use_cases.get_weak_radicals import GetWeakRadicalsUseCase
from app.modules.gamification.domain.achievement_rules import EVENT_METRICS, SIGNAL_METRICS
from app.modules.gamification.domain.entities import (
    AchievementMetric,
    AchievementSource,
    LeaderboardMetric,
    LeaderboardPeriod,
    UserAchievement,
)
from app.modules.gamification.domain.errors import AchievementLockedError, AchievementNotFoundError
from app.modules.gamification.domain.minigame_rules import WeakRadical, weak_radicals
from tests.conftest import FixedClock
from tests.unit.gamification_fakes import FakeGamification, utc

ME = Identity(user_id=1, role=Role.USER, session_id="s")
NOW = utc(2026, 10, 28, 3)


class _Notices:
    async def send(self, notice: Notice) -> None:
        return None


def _unlock(store: FakeGamification, code: str, tier: int = 1) -> None:
    achievement = next(a for a in store.achievements.definitions if a.code == code)
    row = UserAchievement(1, achievement.id, tier, AchievementSource.RULE, False, NOW, NOW)
    store.achievements.rows[(1, achievement.id)] = row


async def test_equip_requires_unlocked_badge_and_keeps_at_most_one_equipped() -> None:
    """US-NH-92: chỉ đeo huy hiệu đã mở khóa; đeo cái mới thì cái cũ được bỏ; null để tháo."""
    store = FakeGamification()
    use_case = EquipAchievementUseCase(lambda: store)  # type: ignore[arg-type,return-value]
    with pytest.raises(AchievementLockedError):
        await use_case.execute(ME, "night_owl")
    with pytest.raises(AchievementNotFoundError):
        await use_case.execute(ME, "khong_co")

    _unlock(store, "night_owl", 2)
    _unlock(store, "manhua_elite", 1)
    first = await use_case.execute(ME, "night_owl")
    assert (first.code, first.tier) == ("night_owl", 2)
    await use_case.execute(ME, "manhua_elite")
    equipped = [r for r in store.achievements.rows.values() if r.is_equipped]
    assert len(equipped) == 1 and equipped[0].achievement_id == 3

    cleared = await use_case.execute(ME, None)
    assert cleared.code is None
    assert not any(r.is_equipped for r in store.achievements.rows.values())


async def test_failed_equip_keeps_current_badge() -> None:
    """US-NH-92 TC (ngoại lệ): đeo huy hiệu chưa mở khóa thì huy hiệu đang đeo giữ nguyên."""
    store = FakeGamification()
    use_case = EquipAchievementUseCase(lambda: store)  # type: ignore[arg-type,return-value]
    _unlock(store, "night_owl")
    await use_case.execute(ME, "night_owl")
    with pytest.raises(AchievementLockedError):
        await use_case.execute(ME, "hsk3_master")
    assert [r.achievement_id for r in store.achievements.rows.values() if r.is_equipped] == [6]


def _chars(store: FakeGamification) -> None:
    for ch in "氵河海湖":
        store.chars.add(ch, "氵")
    for ch in "木林森":
        store.chars.add(ch, "木")


def test_weak_radicals_count_parts_and_apply_threshold() -> None:
    """US-NH-81 TC1: đếm bộ thủ/thành phần của chữ hay quên, lấy tối đa 3 bộ đạt ngưỡng 3 lần."""
    store = FakeGamification()
    _chars(store)
    store.chars.add("江", "氵", ("工",))
    counts = {"河": 2, "海": 2, "江": 1, "林": 2}
    result = weak_radicals(counts, store.chars.infos)
    assert result == [WeakRadical("氵", 5)]  # 木 chỉ có 2 lần, chưa đủ ngưỡng 3


async def test_weak_radicals_fall_back_to_common_radicals_without_review_data() -> None:
    """US-NH-81 TC (ngoại lệ): chưa có dữ liệu ôn tập thì gợi ý bộ thủ phổ biến kèm thông báo."""
    store = FakeGamification()
    store.chars.common = [WeakRadical("口", 40)]
    view = await GetWeakRadicalsUseCase(lambda: store, FixedClock(NOW)).execute(ME)  # type: ignore[arg-type,return-value]
    assert view.fallback and view.message == "Chưa có dữ liệu để gợi ý bộ thủ yếu"
    assert [r.radical for r in view.radicals] == ["口"]


def test_instant_badge_triggers_cover_review_mastery_known_words_and_bubble_lookups() -> None:
    """US-NH-91 / F16.11: chấm thẻ, "Đã thuộc" và tra bong bóng đều đánh giá huy hiệu tức thời."""
    assert AchievementMetric.HSK3_MASTERED in EVENT_METRICS[LearningSource.REVIEW]
    assert SIGNAL_METRICS[LearningSignal.VOCAB_MASTERED] == frozenset({AchievementMetric.HSK3_MASTERED})
    assert SIGNAL_METRICS[LearningSignal.BUBBLE_LOOKUP] == frozenset({AchievementMetric.BUBBLE_LOOKUPS})


def _entry(uid: int, rank: int, score: int, name: str, show: bool) -> LeaderboardEntry:
    return LeaderboardEntry(uid, rank, score, name, 9, "preset", 4, show)


async def test_leaderboard_shows_hidden_users_as_anonymous_but_keeps_rank_and_my_row_full() -> None:
    """US-NH-89 TC2, TC3: người ẩn hiện "Học viên ẩn danh" với người khác, giữ hạng, điểm; dòng của tôi đủ."""
    store = FakeGamification()
    store.users.set(1, display_name="Tôi", show_on_leaderboard=False)
    store.leaderboard.entries = [
        _entry(2, 1, 500, "Người Hai", True),
        _entry(3, 2, 400, "Người Ba", False),
        _entry(1, 3, 300, "Tôi", False),
    ]
    use_case = GetLeaderboardUseCase(lambda: store, FixedClock(NOW))  # type: ignore[arg-type,return-value]
    view = await use_case.execute(ME, LeaderboardMetric.EXP, LeaderboardPeriod.WEEK, 1, 50)
    first, hidden, mine = view.items
    assert (first.display_name, first.anonymous) == ("Người Hai", False)
    assert (hidden.display_name, hidden.anonymous, hidden.rank, hidden.score) == (
        "Học viên ẩn danh",
        True,
        2,
        400,
    )
    assert hidden.avatar_preset is None and hidden.hsk_level is None and hidden.badge is None
    assert (mine.display_name, mine.is_me, mine.anonymous) == ("Tôi", True, False)
    assert view.me_hidden and view.me.rank == 3 and view.me.display_name == "Tôi"
    # Hạng 3 nhắm mốc hạng 1 (500 XP): cần 500 - 300 + 1 XP để vượt.
    assert view.next_milestone is not None
    assert (view.next_milestone.rank, view.next_milestone.xp_missing) == (1, 201)
    assert view.summary.learners == 3


async def test_leaderboard_me_row_exists_even_without_score() -> None:
    """US-NH-88 TC (ngoại lệ): chưa có điểm thì dòng "Bạn" hiện 0 điểm, danh sách rỗng không lỗi."""
    store = FakeGamification()
    use_case = GetLeaderboardUseCase(lambda: store, FixedClock(NOW))  # type: ignore[arg-type,return-value]
    view = await use_case.execute(ME, LeaderboardMetric.PAGES, LeaderboardPeriod.ALL, 1, 50)
    assert view.items == [] and view.me.rank is None and view.me.score == 0 and view.me.unit == "trang"
