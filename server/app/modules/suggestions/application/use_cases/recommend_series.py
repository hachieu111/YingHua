from __future__ import annotations

from app.modules.auth.application.public import Identity
from app.modules.suggestions.application.dto import SeriesRecommendations
from app.modules.suggestions.application.ports import LearnerLevelSource, SeriesCandidateSource
from app.modules.suggestions.domain.rules import level_window, recommend_series


class RecommendSeriesUseCase:
    """F10.04 — Gợi ý 1–3 truyện công khai theo trình độ HSK của người học (US-NH-72).

    Lấy truyện có cấp ước tính bằng trình độ hoặc cao hơn 1 cấp; truyện đã có trong Thư viện hoặc đã đọc xong
    xếp sau; sắp theo điểm đánh giá. Chưa khai báo trình độ: trả `hsk_level=None` (giao diện nhắc khai báo)
    kèm truyện phổ biến cấp thấp. Tính khi yêu cầu, không lưu. Không có truyện phù hợp → danh sách rỗng.
    """

    def __init__(self, series: SeriesCandidateSource, levels: LearnerLevelSource) -> None:
        self._series = series
        self._levels = levels

    async def execute(self, identity: Identity, limit: int) -> SeriesRecommendations:
        level = await self._levels.hsk_level_of(identity.user_id)
        low, high = level_window(level)
        candidates = await self._series.candidates(identity, low, high)
        return SeriesRecommendations(level, recommend_series(candidates, level, limit))
