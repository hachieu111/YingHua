from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta

from app.modules.gamification.application.achievement_engine import AchievementEngine
from app.modules.gamification.application.dto import FinalizeReport, Notice
from app.modules.gamification.application.ports import GamificationUnitOfWork, NoticeSender
from app.modules.gamification.application.season_rewards import SEASON_BADGES, SEASON_REWARDS, season_key
from app.modules.gamification.domain.entities import Season, SeasonResult, SeasonStatus
from app.modules.gamification.domain.season_rules import (
    SEASON_CATCHUP_WEEKS,
    SEASON_DAYS,
    SEASON_MIN_XP,
    SEASON_TOP_N,
    LeaderboardWindow,
    season_bounds,
    tier_for_rank,
    vn_date,
)
from app.modules.notifications.application.public import NotificationKind
from app.modules.rewards.application.public import LedgerReason

logger = logging.getLogger(__name__)


class FinalizeSeasonsUseCase:
    """F16.10 - Chốt mùa đã kết thúc và trao thưởng tự động (US-HG-05). Do tác vụ nền `finalize_seasons` gọi.

    1. Tạo bù mùa còn thiếu cho các tuần đã có sự kiện XP, và mùa của tuần hiện hành (mùa kế tiếp).
    2. Với mỗi mùa quá hạn chưa xong (`active`/`finalizing`, khóa `SKIP LOCKED`): `active` thì xếp hạng theo
       điểm của sự kiện XP (chốt muộn không đổi kết quả), ghi top 50 đủ điều kiện rồi chuyển `finalizing`.
    3. Mỗi người chưa được trao: giao dịch RIÊNG gồm trao thưởng bậc (M17, khóa `season:<mã mùa>`), huy hiệu
       mùa và đặt `reward_granted_at`; thông báo gửi SAU khi lưu. Lỗi ở một người chỉ ghi log, mùa giữ
       `finalizing`
       để lần chạy sau trao tiếp. Chạy lại không trao lần hai.
    4. Hết người chưa trao thì mùa thành `finalized`.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], notices: NoticeSender) -> None:
        self._uow_factory = uow_factory
        self._notices = notices

    async def execute(self, now: datetime) -> FinalizeReport:
        created = await self._ensure_seasons(now)
        rewarded: Counter[str] = Counter()
        finalized = failed = pending = 0
        skip_seasons: list[int] = []
        while (season := await self._open_next(now, skip_seasons)) is not None:
            failed_users: list[int] = []
            while await self._grant_next(season, now, failed_users, rewarded):
                pass
            failed += len(failed_users)
            if await self._close_if_done(season, now):
                finalized += 1
            else:
                pending += 1
                skip_seasons.append(season.id)
        return FinalizeReport(created, finalized, dict(rewarded), failed, pending)

    async def _ensure_seasons(self, now: datetime) -> int:
        created = 0
        async with self._uow_factory() as uow:
            since = now - timedelta(weeks=SEASON_CATCHUP_WEEKS)
            for start in await uow.seasons.missing_week_starts(since, now):
                _, new = await uow.seasons.ensure(start, start + timedelta(days=SEASON_DAYS), now)
                created += int(new)
            _, new = await uow.seasons.ensure(*season_bounds(now), now)
            created += int(new)
            await uow.commit()
        return created

    async def _open_next(self, now: datetime, skip: list[int]) -> Season | None:
        """Khóa một mùa quá hạn; nếu còn `active` thì ghi kết quả top 50 và chuyển `finalizing`."""
        async with self._uow_factory() as uow:
            season = await uow.seasons.claim_ended(now, skip)
            if season is None:
                return None
            if season.status is SeasonStatus.ACTIVE:
                window = LeaderboardWindow(
                    season.starts_at,
                    season.ends_at,
                    vn_date(season.starts_at),
                    vn_date(season.ends_at) - timedelta(days=1),
                    vn_date(now),
                )
                ranked = await uow.leaderboard.top_exp(window, SEASON_TOP_N, SEASON_MIN_XP)
                results = [
                    SeasonResult(season.id, r.user_id, r.rank, r.score, tier)
                    for r in ranked
                    if (tier := tier_for_rank(r.rank)) is not None
                ]
                await uow.seasons.add_results(results, now)
                await uow.seasons.set_status(season.id, SeasonStatus.FINALIZING, None)
                await uow.commit()
            return season

    async def _grant_next(
        self, season: Season, now: datetime, failed_users: list[int], rewarded: Counter[str]
    ) -> bool:
        """Trao cho một người chưa nhận. True = còn việc thử tiếp, False = hết người hoặc không nhận việc."""
        result: SeasonResult | None = None
        pending: list[Notice] = []
        try:
            async with self._uow_factory() as uow:
                result = await uow.seasons.claim_pending_result(season.id, failed_users)
                if result is None:
                    return False
                await self._grant(uow, season, result, now, pending)
                await uow.seasons.mark_granted(season.id, result.user_id, now)
                await uow.commit()
        except Exception:
            logger.exception("Không trao được thưởng mùa %s", season.id)
            if result is None:
                return False  # lỗi ngay lúc nhận việc: dừng để khỏi lặp vô hạn, lần chạy sau thử lại
            failed_users.append(result.user_id)
            return True
        rewarded[result.tier.value] += 1
        for notice in pending:
            await self._notices.send(notice)
        return True

    @staticmethod
    async def _grant(
        uow: GamificationUnitOfWork,
        season: Season,
        result: SeasonResult,
        now: datetime,
        pending: list[Notice],
    ) -> None:
        await uow.rewards.grant(
            result.user_id,
            SEASON_REWARDS[result.tier],
            season_key(season.id),
            LedgerReason.SEASON_REWARD,
            now,
        )
        pending.append(
            Notice(
                result.user_id,
                NotificationKind.SEASON_REWARD.value,
                f"Bạn đạt hạng {result.rank} mùa thi đua kỳ {season.number}",
                f"Phần thưởng bậc {result.tier.value} đã được cộng vào ví của bạn.",
                {
                    "season_id": season.id,
                    "season_number": season.number,
                    "rank": result.rank,
                    "tier": result.tier.value,
                },
            )
        )
        badge = SEASON_BADGES.get(result.tier)
        if badge is not None:
            await AchievementEngine(uow).award_season_badge(result.user_id, badge, now, pending)

    async def _close_if_done(self, season: Season, now: datetime) -> bool:
        async with self._uow_factory() as uow:
            if await uow.seasons.count_pending(season.id) > 0:
                return False
            await uow.seasons.set_status(season.id, SeasonStatus.FINALIZED, now)
            await uow.commit()
            return True
