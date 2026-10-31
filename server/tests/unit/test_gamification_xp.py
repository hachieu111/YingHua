"""M16 - Ghi nhận XP, trần ngày, nhiệm vụ, mục tiêu tuần, mốc chuỗi, huy hiệu (F16.02, F16.04–F16.06, F16.11).

Tiêu chí lấy từ US-NH-84 … US-NH-87, US-NH-91. Dùng bản giả của kho và đồng hồ cố định.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.core.learning_events import LearningEvent, LearningSource
from app.modules.gamification.application.dto import Notice
from app.modules.gamification.application.recorder import EventRecorder
from app.modules.gamification.domain.entities import AchievementMetric, XpSource
from app.modules.rewards.application.public import FrameSource, LedgerReason
from tests.unit.gamification_fakes import FakeGamification, utc

# 10:00 Thứ Tư 28/10/2026 giờ Việt Nam; tuần bắt đầu Thứ Hai 26/10.
NOW = utc(2026, 10, 28, 3)
TODAY = date(2026, 10, 28)
MONDAY = date(2026, 10, 26)


def _event(
    source: LearningSource, ref: str, *, user: int = 1, at: datetime = NOW, **numbers: int
) -> LearningEvent:
    return LearningEvent(user, source, ref, at, **numbers)


async def _record(store: FakeGamification, event: LearningEvent, notices: list[Notice] | None = None) -> int:
    return await EventRecorder(store).record(event, notices if notices is not None else [])


async def test_same_page_read_adds_xp_only_once() -> None:
    """US-NH-84 TC (chống trùng): đọc lại trang cũ hoặc gửi lại cùng sự kiện không cộng thêm."""
    store = FakeGamification()
    assert await _record(store, _event(LearningSource.PAGE_READ, "77")) == 2
    assert await _record(store, _event(LearningSource.PAGE_READ, "77")) == 0
    assert await store.xp.xp_total(1) == 2


async def test_deleted_and_resaved_word_does_not_add_xp_again() -> None:
    """US-NH-84: khóa chống trùng là vĩnh viễn, lưu lại một từ đã xóa không được thưởng lần hai."""
    store = FakeGamification()
    assert await _record(store, _event(LearningSource.WORD_SAVED, "学习")) == 3
    assert await _record(store, _event(LearningSource.WORD_SAVED, "学习")) == 0


async def test_daily_total_cap_cuts_extra_xp_but_still_records_event_as_capped() -> None:
    """US-NH-84: trần chung 300 XP/ngày; phần vượt bị cắt, sự kiện vẫn được ghi với cờ capped."""
    store = FakeGamification()
    for i in range(100):
        await _record(store, _event(LearningSource.PAGE_READ, f"p{i}"))  # 200 XP
    for i in range(100):
        await _record(store, _event(LearningSource.REVIEW, f"r{i}"))  # 100 XP
    assert await store.xp.activity_xp_for_day(1, TODAY) == 300
    assert await _record(store, _event(LearningSource.REVIEW, "r-extra")) == 0
    extra = store.xp.rows[(1, XpSource.REVIEW, "r-extra")]
    assert (extra.amount, extra.capped) == (0, True)
    assert await store.xp.activity_xp_for_day(1, TODAY) == 300


async def test_quiz_cap_is_five_quizzes_per_day() -> None:
    """US-NH-84: chỉ 5 bài kiểm tra đầu tiên mỗi ngày được tính XP."""
    store = FakeGamification()
    earned = [
        await _record(store, _event(LearningSource.QUIZ, f"q{i}", value=0, answered=5, total=5))
        for i in range(6)
    ]
    assert earned == [10, 10, 10, 10, 10, 0]


async def test_quiz_xp_is_ten_plus_correct_answers_capped_at_twenty() -> None:
    """US-NH-84: bài nộp XP = 10 + số câu đúng, tối đa 20."""
    store = FakeGamification()
    assert await _record(store, _event(LearningSource.QUIZ, "a", value=3, answered=5, total=5)) == 13
    assert await _record(store, _event(LearningSource.QUIZ, "b", value=15, answered=15, total=15)) == 20


async def test_quiz_with_less_than_half_answered_creates_no_xp_event() -> None:
    """US-NH-84: trả lời dưới một nửa số câu không tạo sự kiện XP (chống nộp bài trống)."""
    store = FakeGamification()
    assert await _record(store, _event(LearningSource.QUIZ, "blank", value=0, answered=2, total=5)) == 0
    assert (1, XpSource.QUIZ, "blank") not in store.xp.rows
    assert await _record(store, _event(LearningSource.QUIZ, "half", value=1, answered=3, total=5)) == 11


async def test_minigame_xp_is_half_the_score_capped_at_ten_and_five_games_a_day() -> None:
    """US-NH-81 TC5: XP = điểm chia 2 (làm tròn xuống), tối đa 10; chỉ 5 ván đầu mỗi ngày được tính."""
    store = FakeGamification()
    assert await _record(store, _event(LearningSource.MINIGAME, "1", value=7)) == 3
    assert await _record(store, _event(LearningSource.MINIGAME, "2", value=100)) == 10
    for i in range(3, 6):
        await _record(store, _event(LearningSource.MINIGAME, str(i), value=20))
    assert await _record(store, _event(LearningSource.MINIGAME, "6", value=20)) == 0


async def test_read_two_pages_completes_quest_and_all_three_give_bonus_coins_once() -> None:
    """US-NH-85: nhiệm vụ đạt mục tiêu được thưởng tự động; đủ 3/3 thì +20 xu, mỗi ngày một lần."""
    store = FakeGamification()
    store.activity.add(1, TODAY, pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "1"))
    assert (1, XpSource.QUEST, "read_pages:2026-10-28") not in store.xp.rows
    store.activity.add(1, TODAY, pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "2"))
    assert store.xp.rows[(1, XpSource.QUEST, "read_pages:2026-10-28")].amount == 20

    store.activity.add(1, TODAY, reviews=15)
    await _record(store, _event(LearningSource.REVIEW, "r1"))
    assert store.xp.rows[(1, XpSource.QUEST, "review_cards:2026-10-28")].amount == 15
    assert store.rewards.coins_for(1) == 0

    await _record(store, _event(LearningSource.QUIZ, "q1", value=1, answered=1, total=1))
    assert store.xp.rows[(1, XpSource.QUEST, "take_quiz:2026-10-28")].amount == 30
    assert store.rewards.coins_for(1) == 20
    bonus = [g for g in store.rewards.grants if g[2] == "quests_all:2026-10-28"]
    assert [(g[1].coins, g[3]) for g in bonus] == [(20, LedgerReason.QUEST_BONUS)]

    await _record(store, _event(LearningSource.REVIEW, "r2"))
    assert store.rewards.coins_for(1) == 20


async def test_quest_xp_is_not_limited_by_the_daily_cap() -> None:
    """US-NH-85: XP thưởng nhiệm vụ không bị trần chung của ngày."""
    store = FakeGamification()
    for i in range(100):
        await _record(store, _event(LearningSource.PAGE_READ, f"p{i}"))
        await _record(store, _event(LearningSource.REVIEW, f"r{i}"))
    store.activity.add(1, TODAY, pages=2)
    await _record(store, _event(LearningSource.PAGE_READ, "late"))
    assert store.xp.rows[(1, XpSource.QUEST, "read_pages:2026-10-28")].amount == 20


async def test_weekly_goal_below_ten_pages_still_needs_ten_pages_to_reward() -> None:
    """US-NH-86: mục tiêu đặt dưới 10 trang chỉ được thưởng khi đọc từ 10 trang trong tuần."""
    store = FakeGamification()
    store.users.set(1, weekly_page_goal=3)
    for i in range(9):
        store.activity.add(1, MONDAY + timedelta(days=i % 3), pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "n9"))
    assert (1, XpSource.WEEKLY_GOAL, "2026-10-26") not in store.xp.rows
    store.activity.add(1, TODAY, pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "n10"))
    assert store.xp.rows[(1, XpSource.WEEKLY_GOAL, "2026-10-26")].amount == 150


async def test_weekly_goal_rewards_once_per_week_with_seven_day_frame() -> None:
    """US-NH-86: đạt mục tiêu thưởng +150 XP và khung Hoa Anh Đào Vàng 7 ngày, mỗi tuần một lần."""
    store = FakeGamification()
    store.users.set(1, weekly_page_goal=12)
    for i in range(12):
        store.activity.add(1, MONDAY + timedelta(days=i % 3), pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "w1"))
    store.activity.add(1, TODAY, pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "w2"))
    frames = [g[1].frame for g in store.rewards.grants if g[1].frame is not None]
    assert len(frames) == 1
    assert (frames[0].code, frames[0].source, frames[0].days) == ("sakura_gold", FrameSource.WEEKLY_GOAL, 7)
    store.users.set(1, weekly_page_goal=10)  # đổi mục tiêu sau khi đã thưởng cũng không thưởng lại
    await _record(store, _event(LearningSource.PAGE_READ, "w3"))
    assert len([g for g in store.rewards.grants if g[1].frame is not None]) == 1


async def test_default_weekly_goal_is_twenty_pages() -> None:
    """US-NH-86 TC (người dùng mới): chưa đặt mục tiêu thì mặc định 20 trang."""
    store = FakeGamification()
    for i in range(19):
        store.activity.add(1, MONDAY + timedelta(days=i % 3), pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "a"))
    assert (1, XpSource.WEEKLY_GOAL, "2026-10-26") not in store.xp.rows
    store.activity.add(1, TODAY, pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "b"))
    assert (1, XpSource.WEEKLY_GOAL, "2026-10-26") in store.xp.rows


async def test_seven_day_streak_rewards_once_and_a_new_streak_can_reward_again() -> None:
    """US-NH-87: mỗi mốc thưởng một lần cho mỗi chuỗi; chuỗi đứt rồi bắt đầu lại thì nhận lại từ mốc 7."""
    store = FakeGamification()
    for back in range(6, -1, -1):
        store.activity.add(1, TODAY - timedelta(days=back), reviews=1)
    notices: list[Notice] = []
    await _record(store, _event(LearningSource.REVIEW, "r1"), notices)
    ref = "7:2026-10-22"
    assert store.xp.rows[(1, XpSource.STREAK_MILESTONE, ref)].amount == 50
    assert store.rewards.coins_for(1) == 50
    assert [n.kind for n in notices] == ["streak_milestone"]

    await _record(store, _event(LearningSource.REVIEW, "r2"), notices)
    assert store.rewards.coins_for(1) == 50 and len(notices) == 1

    # Chuỗi mới sau khi đứt: 7 ngày liên tiếp bắt đầu từ 11/11 -> khóa khác -> thưởng lại.
    later = utc(2026, 11, 17, 3)
    for back in range(6, -1, -1):
        store.activity.add(1, date(2026, 11, 17) - timedelta(days=back), reviews=1)
    await _record(store, _event(LearningSource.REVIEW, "r3", at=later), notices)
    assert (1, XpSource.STREAK_MILESTONE, "7:2026-11-11") in store.xp.rows
    assert store.rewards.coins_for(1) == 100


async def test_thirty_day_streak_gives_vip_days_and_all_reached_milestones() -> None:
    """US-NH-87: mốc 30 ngày +200 XP, +200 xu, +3 ngày VIP; mốc thấp hơn chưa nhận cũng được trao."""
    store = FakeGamification()
    for back in range(29, -1, -1):
        store.activity.add(1, TODAY - timedelta(days=back), pages=1)
    await _record(store, _event(LearningSource.PAGE_READ, "p"))
    keys = store.rewards.keys_for(1)
    assert "7:2026-09-29" in keys and "30:2026-09-29" in keys
    thirty = next(g for g in store.rewards.grants if g[2] == "30:2026-09-29")
    assert (thirty[1].coins, thirty[1].vip_days) == (200, 3)


async def test_yesterday_streak_without_today_study_does_not_reward_new_day() -> None:
    """F12.02: hôm nay chưa học thì chuỗi vẫn giữ; sự kiện không tính chuỗi (lưu từ) không kích hoạt mốc."""
    store = FakeGamification()
    for back in range(7, 0, -1):
        store.activity.add(1, TODAY - timedelta(days=back), reviews=1)
    await _record(store, _event(LearningSource.WORD_SAVED, "từ"))
    assert not any(k[1] is XpSource.STREAK_MILESTONE for k in store.xp.rows)


async def test_achievement_tiers_pay_coins_per_tier_and_never_revoke() -> None:
    """US-NH-91: vượt nhiều cấp cùng lúc thì trao đủ xu từng cấp; số liệu giảm không thu hồi huy hiệu."""
    store = FakeGamification()
    store.metrics.data[AchievementMetric.PAGES_READ] = 120
    notices: list[Notice] = []
    await _record(store, _event(LearningSource.PAGE_READ, "a"), notices)
    assert "achievement:manhua_elite:1" in store.rewards.keys_for(1)
    assert [n.kind for n in notices] == ["achievement_unlocked"]

    store.metrics.data[AchievementMetric.PAGES_READ] = 600
    await _record(store, _event(LearningSource.PAGE_READ, "b"), notices)
    keys = store.rewards.keys_for(1)
    assert keys.count("achievement:manhua_elite:1") == 1 and "achievement:manhua_elite:2" in keys

    store.metrics.data[AchievementMetric.PAGES_READ] = 0  # xóa truyện làm số liệu giảm
    await _record(store, _event(LearningSource.PAGE_READ, "c"), notices)
    row = next(r for r in store.achievements.rows.values() if r.user_id == 1)
    assert row.tier == 2


async def test_event_on_a_different_local_day_uses_the_learner_timezone() -> None:
    """US-NH-84: ngày của trần và nhiệm vụ tính theo múi giờ của người học (F12.02)."""
    store = FakeGamification()
    store.users.set(1, timezone="America/New_York")
    at = utc(2026, 10, 28, 3)  # vẫn là 27/10 ở New York
    await _record(store, _event(LearningSource.PAGE_READ, "ny", at=at))
    assert store.xp.rows[(1, XpSource.PAGE_READ, "ny")].activity_date == date(2026, 10, 27)
