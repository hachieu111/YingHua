"""Nạp bù `daily_activities` từ dữ liệu cũ (chạy một lần, chạy lại không nhân đôi).

Mỗi câu lệnh TÍNH LẠI một bộ đếm từ bảng nguồn rồi GHI ĐÈ (`SET = EXCLUDED`), không cộng dồn, nên chạy lại
cho kết quả y hệt. Công thức khớp với lúc ghi trực tiếp: ngày theo múi giờ người học, thời gian học làm tròn
và chặn trần giống `study_seconds_from_ms`. Đọc thẳng các bảng nguồn bằng SQL có tham số (chỉ-đọc, một lần).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.domain.entities import DEFAULT_TIMEZONE
from app.modules.stats.domain.activity import MAX_STUDY_MS_PER_REVIEW

_LOCAL_DAY = "(src.{col} AT TIME ZONE COALESCE(us.timezone, :tz))::date"

_REVIEWS = f"""
INSERT INTO daily_activities (user_id, activity_date, reviews_count, study_seconds, updated_at)
SELECT src.user_id, {_LOCAL_DAY.format(col="reviewed_at")} AS d, COUNT(*),
       SUM((LEAST(COALESCE(src.duration_ms, 0), :cap_ms) + 500) / 1000), now()
FROM review_logs src LEFT JOIN user_settings us ON us.user_id = src.user_id
GROUP BY src.user_id, d
ON CONFLICT (user_id, activity_date) DO UPDATE
SET reviews_count = EXCLUDED.reviews_count, study_seconds = EXCLUDED.study_seconds, updated_at = now()
"""

_PAGES = f"""
INSERT INTO daily_activities (user_id, activity_date, pages_read, updated_at)
SELECT src.user_id, {_LOCAL_DAY.format(col="first_read_at")} AS d, COUNT(*), now()
FROM page_reads src LEFT JOIN user_settings us ON us.user_id = src.user_id
GROUP BY src.user_id, d
ON CONFLICT (user_id, activity_date) DO UPDATE SET pages_read = EXCLUDED.pages_read, updated_at = now()
"""

_WORDS = f"""
INSERT INTO daily_activities (user_id, activity_date, words_saved, updated_at)
SELECT src.user_id, {_LOCAL_DAY.format(col="created_at")} AS d, COUNT(*), now()
FROM vocab_entries src LEFT JOIN user_settings us ON us.user_id = src.user_id
GROUP BY src.user_id, d
ON CONFLICT (user_id, activity_date) DO UPDATE SET words_saved = EXCLUDED.words_saved, updated_at = now()
"""

_QUIZZES = f"""
INSERT INTO daily_activities (user_id, activity_date, quizzes_done, updated_at)
SELECT src.user_id, {_LOCAL_DAY.format(col="submitted_at")} AS d, COUNT(*), now()
FROM quizzes src LEFT JOIN user_settings us ON us.user_id = src.user_id
WHERE src.status = 'submitted' AND src.submitted_at IS NOT NULL
GROUP BY src.user_id, d
ON CONFLICT (user_id, activity_date) DO UPDATE SET quizzes_done = EXCLUDED.quizzes_done, updated_at = now()
"""


class SqlActivityBackfill:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(self) -> dict[str, int]:
        """Chạy lần lượt bốn nguồn; trả số dòng (người, ngày) đã ghi cho từng nguồn."""
        tz: dict[str, object] = {"tz": DEFAULT_TIMEZONE}
        steps: list[tuple[str, str, dict[str, object]]] = [
            ("reviews", _REVIEWS, {**tz, "cap_ms": MAX_STUDY_MS_PER_REVIEW}),
            ("pages", _PAGES, tz),
            ("words", _WORDS, tz),
            ("quizzes", _QUIZZES, tz),
        ]
        report: dict[str, int] = {}
        for name, sql, params in steps:
            result = await self._session.execute(text(sql), params)
            report[name] = int(getattr(result, "rowcount", 0) or 0)
        return report
