"""Bảng xếp hạng tính khi gọi bằng SUM/CTE trên sổ XP và `daily_activities` (F16.07).

SQL thô vì cần hàm cửa sổ và CTE; luôn dùng tham số bind. Các mảnh SQL ghép lại đều là hằng số của file này
(không có chuỗi nào đến từ người dùng); `metric` đã là enum.

Thứ tự hạng: điểm giảm dần, ai đạt điểm đó sớm hơn đứng trên (hoạt động tính điểm cuối cùng sớm hơn; với chuỗi
ngày là chuỗi bắt đầu sớm hơn), rồi tài khoản tạo sớm hơn, rồi mã nhỏ hơn. Chỉ tính tài khoản đang hoạt động
(tài khoản bị khóa bị loại; quản trị viên được xếp hạng).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.application.dto import LeaderboardEntry, LeaderboardTotals, RankedScore
from app.modules.gamification.domain.entities import LeaderboardMetric
from app.modules.gamification.domain.season_rules import LeaderboardWindow

_SCORES: dict[LeaderboardMetric, str] = {
    LeaderboardMetric.EXP: """
        SELECT e.user_id, SUM(e.amount)::bigint AS score, MAX(e.created_at) AS reached_at
        FROM xp_events e
        WHERE e.created_at >= CAST(:start_at AS timestamptz) AND e.created_at < CAST(:end_at AS timestamptz)
        GROUP BY e.user_id HAVING SUM(e.amount) > 0""",
    LeaderboardMetric.VOCAB: """
        SELECT a.user_id, SUM(a.words_saved)::bigint AS score, MAX(a.updated_at) AS reached_at
        FROM daily_activities a
        WHERE a.activity_date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
          AND a.words_saved > 0
        GROUP BY a.user_id""",
    LeaderboardMetric.PAGES: """
        SELECT a.user_id, SUM(a.pages_read)::bigint AS score, MAX(a.updated_at) AS reached_at
        FROM daily_activities a
        WHERE a.activity_date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
          AND a.pages_read > 0
        GROUP BY a.user_id""",
    # Chuỗi hiện tại (F12.02): đoạn ngày liên tiếp kết thúc hôm nay hoặc hôm qua; không phụ thuộc khoảng.
    LeaderboardMetric.STREAK: """
        WITH days AS (
            SELECT d.user_id, d.activity_date,
                   d.activity_date - (ROW_NUMBER() OVER (
                       PARTITION BY d.user_id ORDER BY d.activity_date))::int AS grp
            FROM daily_activities d WHERE d.reviews_count + d.pages_read > 0),
        islands AS (
            SELECT user_id, COUNT(*)::bigint AS len, MIN(activity_date) AS first_day,
                   MAX(activity_date) AS last_day
            FROM days GROUP BY user_id, grp)
        SELECT user_id, len AS score, CAST(first_day AS timestamp) AT TIME ZONE 'UTC' AS reached_at
        FROM islands WHERE last_day >= CAST(:today AS date) - 1""",
}

_RANKED = """
    r AS (
        SELECT s.user_id, s.score,
               ROW_NUMBER() OVER (ORDER BY s.score DESC, s.reached_at ASC, u.created_at ASC, u.id ASC) AS rank
        FROM s JOIN users u ON u.id = s.user_id
        WHERE u.status = 'active')"""


def _query(metric: LeaderboardMetric, tail: str) -> Any:
    return text(f"WITH s AS ({_SCORES[metric]}), {_RANKED} {tail}")


def _params(window: LeaderboardWindow, **extra: Any) -> dict[str, Any]:
    return {
        "start_at": window.start_at,
        "end_at": window.end_at,
        "start_date": window.start_date,
        "end_date": window.end_date,
        "today": window.today,
        **extra,
    }


class SqlLeaderboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def page(
        self, metric: LeaderboardMetric, window: LeaderboardWindow, offset: int, limit: int
    ) -> tuple[list[LeaderboardEntry], int]:
        rows = await self._session.execute(
            _query(
                metric,
                """SELECT r.rank, r.score, u.id AS user_id, u.display_name, u.avatar_file_id, u.avatar_preset,
                          us.hsk_level, COALESCE(us.show_on_leaderboard, TRUE) AS show_on_leaderboard
                   FROM r JOIN users u ON u.id = r.user_id
                   LEFT JOIN user_settings us ON us.user_id = u.id
                   ORDER BY r.rank OFFSET :offset LIMIT :limit""",
            ),
            _params(window, offset=offset, limit=limit),
        )
        entries = [
            LeaderboardEntry(
                user_id=int(m["user_id"]),
                rank=int(m["rank"]),
                score=int(m["score"]),
                display_name=str(m["display_name"]),
                avatar_file_id=m["avatar_file_id"],
                avatar_preset=m["avatar_preset"],
                hsk_level=m["hsk_level"],
                show_on_leaderboard=bool(m["show_on_leaderboard"]),
            )
            for m in rows.mappings()
        ]
        total = await self._session.scalar(_query(metric, "SELECT COUNT(*) FROM r"), _params(window))
        return entries, int(total or 0)

    async def rank_of(
        self, metric: LeaderboardMetric, window: LeaderboardWindow, user_id: int
    ) -> RankedScore | None:
        row = (
            await self._session.execute(
                _query(metric, "SELECT user_id, rank, score FROM r WHERE user_id = :user_id"),
                _params(window, user_id=user_id),
            )
        ).first()
        return RankedScore(int(row[0]), int(row[1]), int(row[2])) if row else None

    async def score_at_rank(
        self, metric: LeaderboardMetric, window: LeaderboardWindow, rank: int
    ) -> int | None:
        value = await self._session.scalar(
            _query(metric, "SELECT score FROM r WHERE rank = :rank"), _params(window, rank=rank)
        )
        return None if value is None else int(value)

    async def top_exp(self, window: LeaderboardWindow, limit: int, min_xp: int) -> list[RankedScore]:
        rows = await self._session.execute(
            _query(
                LeaderboardMetric.EXP,
                "SELECT user_id, rank, score FROM r WHERE score >= :min_xp ORDER BY rank LIMIT :limit",
            ),
            _params(window, min_xp=min_xp, limit=limit),
        )
        return [RankedScore(int(u), int(rank), int(score)) for u, rank, score in rows]

    async def totals(self, window: LeaderboardWindow, season_window: LeaderboardWindow) -> LeaderboardTotals:
        row = (
            await self._session.execute(
                text(
                    """SELECT
                        (SELECT COUNT(*) FROM users WHERE status = 'active') AS learners,
                        (SELECT COALESCE(SUM(pages_read), 0) FROM daily_activities
                          WHERE activity_date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                        ) AS pages,
                        (SELECT COALESCE(SUM(amount), 0) FROM xp_events
                          WHERE created_at >= CAST(:season_start AS timestamptz)
                            AND created_at < CAST(:season_end AS timestamptz)) AS season_xp"""
                ),
                {
                    "start_date": window.start_date,
                    "end_date": window.end_date,
                    "season_start": season_window.start_at,
                    "season_end": season_window.end_at,
                },
            )
        ).one()
        return LeaderboardTotals(int(row[0]), int(row[1]), int(row[2]))
