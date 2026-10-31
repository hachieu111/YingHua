"""M16 - Mùa thi đua theo giờ Việt Nam và chốt mùa (F16.09, F16.10). US-NH-90, US-HG-05."""

from __future__ import annotations

import pytest

from app.modules.gamification.application.dto import Notice, RankedScore
from app.modules.gamification.application.use_cases.finalize_seasons import FinalizeSeasonsUseCase
from app.modules.gamification.domain.entities import (
    AchievementSource,
    LeaderboardPeriod,
    Season,
    SeasonStatus,
    SeasonTier,
)
from app.modules.gamification.domain.season_rules import (
    leaderboard_window,
    next_milestone_rank,
    season_bounds,
    tier_for_rank,
    xp_needed_for_milestone,
)
from app.modules.rewards.application.public import FrameSource, LedgerReason
from tests.unit.gamification_fakes import FakeGamification, utc


class RecordingNotices:
    def __init__(self) -> None:
        self.sent: list[Notice] = []

    async def send(self, notice: Notice) -> None:
        self.sent.append(notice)


def test_season_boundary_is_monday_midnight_vietnam_time() -> None:
    """US-NH-90: mùa từ Thứ Hai 00:00 đến Chủ Nhật 23:59:59 giờ Việt Nam (UTC+7)."""
    last_second = utc(2026, 10, 25, 16, 59, 59)  # Chủ Nhật 23:59:59 giờ VN
    first_second = utc(2026, 10, 25, 17, 0, 0)  # Thứ Hai 00:00:00 giờ VN
    assert season_bounds(last_second) == (utc(2026, 10, 18, 17), utc(2026, 10, 25, 17))
    assert season_bounds(first_second) == (utc(2026, 10, 25, 17), utc(2026, 11, 1, 17))
    # Mốc kết thúc là loại trừ: sự kiện đúng 00:00 Thứ Hai thuộc mùa sau.
    assert season_bounds(utc(2026, 10, 25, 17))[0] == season_bounds(utc(2026, 10, 25, 16, 59, 59))[1]


def test_month_window_follows_vietnam_calendar_month() -> None:
    """F16.07: bảng tháng tính từ ngày 1 00:00 giờ VN."""
    window = leaderboard_window(LeaderboardPeriod.MONTH, utc(2026, 10, 31, 20))  # 01/11 03:00 giờ VN
    assert window.start_at == utc(2026, 10, 31, 17) and window.end_at == utc(2026, 11, 30, 17)


@pytest.mark.parametrize(
    ("rank", "tier"),
    [
        (1, SeasonTier.TOP3),
        (3, SeasonTier.TOP3),
        (4, SeasonTier.TOP10),
        (10, SeasonTier.TOP10),
        (11, SeasonTier.TOP50),
        (50, SeasonTier.TOP50),
        (51, None),
        (0, None),
    ],
)
def test_tier_for_rank(rank: int, tier: SeasonTier | None) -> None:
    """US-NH-90: bậc top 1-3, 4-10, 11-50."""
    assert tier_for_rank(rank) is tier


def test_next_milestone_is_the_closest_reward_rank_above_me() -> None:
    """F16.07 bước 6: mốc 50, 10, 3, 1; chưa có hạng thì nhắm hạng 50."""
    assert [next_milestone_rank(r) for r in (None, 70, 50, 11, 10, 4, 3, 2, 1)] == [
        50, 50, 10, 10, 3, 3, 1, 1, None,
    ]  # fmt: skip
    assert xp_needed_for_milestone(40, 120) == 81
    assert xp_needed_for_milestone(10, None) == 40  # chưa ai giữ mốc: cần tối thiểu 50 XP


def _ended_season(store: FakeGamification) -> Season:
    start, end = season_bounds(utc(2026, 10, 14))
    season = Season(1, 1, start, end, SeasonStatus.ACTIVE)
    store.seasons.seasons[1] = season
    return season


def _use_case(store: FakeGamification, notices: RecordingNotices) -> FinalizeSeasonsUseCase:
    return FinalizeSeasonsUseCase(lambda: store, notices)  # type: ignore[arg-type,return-value]


def _ranking(store: FakeGamification, count: int) -> None:
    store.leaderboard.ranking = [RankedScore(100 + i, i + 1, 1000 - i * 10) for i in range(count)]


async def test_finalize_pays_each_tier_once_and_rerun_pays_nobody_twice() -> None:
    """US-HG-05: mỗi người nhận đúng thưởng của bậc, kèm thông báo; chạy lại không trao lần hai."""
    store, notices = FakeGamification(), RecordingNotices()
    _ended_season(store)
    _ranking(store, 12)
    now = utc(2026, 10, 26, 1)
    report = await _use_case(store, notices).execute(now)
    assert report.rewarded == {"top3": 3, "top10": 7, "top50": 2}
    assert report.seasons_finalized == 1 and report.failed == 0
    assert store.seasons.seasons[1].status is SeasonStatus.FINALIZED

    by_user = {
        uid: (bundle, reason) for uid, bundle, key, reason in store.rewards.grants if key == "season:1"
    }
    top1, _ = by_user[100]
    assert (top1.vip_days, top1.frame.code, top1.frame.source) == (30, "sakura_gold", FrameSource.SEASON)  # type: ignore[union-attr]
    top5 = by_user[104][0]
    assert (top5.tickets, top5.frame.code) == (3, "spring_petal")  # type: ignore[union-attr]
    assert by_user[111][0].coins == 500
    assert all(reason is LedgerReason.SEASON_REWARD for _, reason in by_user.values())

    # Huy hiệu mùa: top 1-3 -> Đệ Nhất Học Giả; top 11-50 -> Người Gieo Hạt cấp I (xu cấp I kèm theo).
    badge = {(uid, aid): r.source for (uid, aid), r in store.achievements.rows.items()}
    assert badge[(100, 2)] is AchievementSource.SEASON and badge[(111, 4)] is AchievementSource.SEASON
    assert (104, 2) not in badge and (104, 4) not in badge
    assert "achievement:seed_sower:1" in store.rewards.keys_for(111)

    kinds = sorted({n.kind for n in notices.sent})
    assert kinds == ["achievement_unlocked", "season_reward"]
    season_notice = next(n for n in notices.sent if n.kind == "season_reward" and n.user_id == 100)
    assert season_notice.data["rank"] == 1 and season_notice.data["season_number"] == 1

    grants_before, sent_before = len(store.rewards.grants), len(notices.sent)
    again = await _use_case(store, notices).execute(now)
    assert again.rewarded == {} and again.seasons_finalized == 0
    assert len(store.rewards.grants) == grants_before and len(notices.sent) == sent_before


async def test_finalize_only_rewards_users_with_at_least_50_xp() -> None:
    """US-NH-90: điều kiện nhận thưởng là có ít nhất 50 XP trong mùa; người ngoài top 50 không nhận."""
    store, notices = FakeGamification(), RecordingNotices()
    _ended_season(store)
    store.leaderboard.ranking = [RankedScore(1, 1, 300), RankedScore(2, 2, 49)]
    await _use_case(store, notices).execute(utc(2026, 10, 26, 1))
    assert {r.user_id for r in store.seasons.results.values()} == {1}
    assert {n.user_id for n in notices.sent} == {1}


async def test_finalize_keeps_season_finalizing_when_one_grant_fails_then_completes() -> None:
    """US-HG-05 (ngoại lệ): lỗi trao cho một người chỉ ghi log; lần chạy sau trao tiếp phần còn thiếu."""
    store, notices = FakeGamification(), RecordingNotices()
    _ended_season(store)
    _ranking(store, 4)
    store.rewards.fail_for = {101}
    now = utc(2026, 10, 26, 1)
    first = await _use_case(store, notices).execute(now)
    assert first.failed == 1 and first.pending_seasons == 1 and first.seasons_finalized == 0
    assert store.seasons.seasons[1].status is SeasonStatus.FINALIZING
    assert {uid for uid, *_ in store.rewards.grants} == {100, 102, 103}

    store.rewards.fail_for = set()
    second = await _use_case(store, notices).execute(now)
    assert second.rewarded == {"top3": 1} and second.seasons_finalized == 1
    assert store.seasons.seasons[1].status is SeasonStatus.FINALIZED
    assert sorted(uid for uid, *_ in store.rewards.grants if uid in (100, 101, 102, 103)) == [
        100,
        101,
        102,
        103,
    ]


async def test_finalize_late_does_not_change_results_and_creates_next_season() -> None:
    """US-HG-05: chốt muộn (máy tắt đúng lúc hết mùa) không đổi kết quả; tự tạo mùa của tuần hiện hành."""
    store, notices = FakeGamification(), RecordingNotices()
    _ended_season(store)
    _ranking(store, 2)
    two_days_late = utc(2026, 10, 28, 5)
    report = await _use_case(store, notices).execute(two_days_late)
    assert [(r.user_id, r.rank) for r in store.seasons.results.values()] == [(100, 1), (101, 2)]
    current = await store.seasons.get_containing(two_days_late)
    assert current is not None and current.number == 2 and current.status is SeasonStatus.ACTIVE
    assert report.seasons_created == 1


async def test_finalize_creates_missing_weeks_that_have_xp() -> None:
    """F16.10 bước 2: tạo bù mùa còn thiếu cho tuần đã có XP mà không ai mở bảng xếp hạng."""
    store, notices = FakeGamification(), RecordingNotices()
    store.seasons.missing = [season_bounds(utc(2026, 10, 7))[0]]
    report = await _use_case(store, notices).execute(utc(2026, 10, 28, 5))
    assert report.seasons_created == 2  # tuần thiếu + tuần hiện hành
    numbers = sorted(s.number for s in store.seasons.seasons.values())
    assert numbers == [1, 2]
