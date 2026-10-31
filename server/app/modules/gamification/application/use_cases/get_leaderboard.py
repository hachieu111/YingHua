from __future__ import annotations

from collections.abc import Callable, Mapping

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import (
    BadgeView,
    BoardRow,
    FrameView,
    LeaderboardEntry,
    LeaderboardView,
    NextMilestone,
    RankedScore,
    UserProfile,
)
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.entities import LeaderboardMetric, LeaderboardPeriod
from app.modules.gamification.domain.season_rules import (
    ANONYMOUS_NAME,
    LeaderboardWindow,
    leaderboard_window,
    metric_unit,
    next_milestone_rank,
    progress_ratio,
    xp_needed_for_milestone,
)
from app.modules.rewards.application.public import Decoration


class GetLeaderboardUseCase:
    """F16.07, F16.08 - Bảng xếp hạng 4 chỉ số x 3 khoảng (US-NH-88, US-NH-89).

    Tính khi gọi từ sổ XP và `daily_activities` (không lưu bảng dựng sẵn). Chỉ xếp tài khoản đang hoạt động
    (tài khoản bị khóa bị loại; quản trị viên được xếp hạng như Người học). Không bao giờ trả email hay mã
    người dùng. Người đã tắt `show_on_leaderboard` hiện "Học viên ẩn danh" với người khác, giữ hạng và điểm;
    với chính họ dòng "Bạn" vẫn đầy đủ. Khung và dấu VIP đọc theo lô (không N+1).
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(
        self, identity: Identity, metric: LeaderboardMetric, period: LeaderboardPeriod, page: int, size: int
    ) -> LeaderboardView:
        uid, now = identity.user_id, self._clock.now()
        window = leaderboard_window(period, now)
        season_window = leaderboard_window(LeaderboardPeriod.WEEK, now)
        async with self._uow_factory() as uow:
            entries, total = await uow.leaderboard.page(metric, window, (page - 1) * size, size)
            mine = await uow.leaderboard.rank_of(metric, window, uid)
            profile = await uow.users.profile(uid)
            shown = [e.user_id for e in entries if e.show_on_leaderboard or e.user_id == uid]
            ids = list(dict.fromkeys([*shown, uid]))
            badges = await uow.achievements.equipped_for(ids)
            decorations = await uow.rewards.decorations(ids, now)
            summary = await uow.leaderboard.totals(window, season_window)
            milestone = None
            if metric is LeaderboardMetric.EXP and period is LeaderboardPeriod.WEEK:
                milestone = await self._milestone(uow, window, mine)
        unit = metric_unit(metric)
        items = [_entry_row(e, uid, unit, badges, decorations) for e in entries]
        return LeaderboardView(
            items=items,
            total=total,
            page=page,
            size=size,
            me=_me_row(profile, mine, unit, badges.get(uid), decorations.get(uid)),
            me_hidden=not profile.show_on_leaderboard,
            next_milestone=milestone,
            summary=summary,
        )

    @staticmethod
    async def _milestone(
        uow: GamificationUnitOfWork, window: LeaderboardWindow, mine: RankedScore | None
    ) -> NextMilestone | None:
        target = next_milestone_rank(mine.rank if mine else None)
        if target is None:
            return None
        holder = await uow.leaderboard.score_at_rank(LeaderboardMetric.EXP, window, target)
        my_xp = mine.score if mine else 0
        return NextMilestone(target, xp_needed_for_milestone(my_xp, holder), progress_ratio(my_xp, holder))


def _decorate(deco: Decoration | None) -> tuple[FrameView | None, bool]:
    if deco is None:
        return None, False
    frame = FrameView(deco.frame.code, deco.frame.name, deco.frame.style_key) if deco.frame else None
    return frame, deco.is_vip


def _entry_row(
    entry: LeaderboardEntry,
    viewer_id: int,
    unit: str,
    badges: Mapping[int, BadgeView],
    decorations: Mapping[int, Decoration],
) -> BoardRow:
    is_me = entry.user_id == viewer_id
    if not entry.show_on_leaderboard and not is_me:
        return BoardRow(
            entry.rank, ANONYMOUS_NAME, None, None, None, entry.score, unit, None, None, False, False, True
        )
    frame, is_vip = _decorate(decorations.get(entry.user_id))
    return BoardRow(
        rank=entry.rank,
        display_name=entry.display_name,
        avatar_file_id=entry.avatar_file_id,
        avatar_preset=entry.avatar_preset,
        hsk_level=entry.hsk_level,
        score=entry.score,
        unit=unit,
        badge=badges.get(entry.user_id),
        frame=frame,
        is_vip=is_vip,
        is_me=is_me,
        anonymous=False,
    )


def _me_row(
    profile: UserProfile,
    mine: RankedScore | None,
    unit: str,
    badge: BadgeView | None,
    deco: Decoration | None,
) -> BoardRow:
    frame, is_vip = _decorate(deco)
    return BoardRow(
        rank=mine.rank if mine else None,
        display_name=profile.display_name,
        avatar_file_id=profile.avatar_file_id,
        avatar_preset=profile.avatar_preset,
        hsk_level=profile.hsk_level,
        score=mine.score if mine else 0,
        unit=unit,
        badge=badge,
        frame=frame,
        is_vip=is_vip,
        is_me=True,
        anonymous=False,
    )
