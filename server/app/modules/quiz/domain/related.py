"""Từ mở rộng trong bài kiểm tra (F09.09, US-NH-69): tỉ lệ, điểm ứng viên, bốc có trọng số, gợi ý.

Điểm của từ mở rộng được TÍNH RIÊNG với điểm từ đã lưu và không ảnh hưởng lịch ôn FSRS.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from app.core.common_chars import is_common_char
from app.core.glosses import short_meaning
from app.modules.quiz.domain.entities import RelatedCandidate, RelatedLink, RelatedSource

RELATED_RATIO = 0.15  # tỉ lệ câu từ mở rộng trong một bài

# Trọng số cộng dồn theo nguồn (đề xuất): chung chữ Hán mạnh nhất, cùng cấp HSK yếu nhất.
SOURCE_WEIGHTS: dict[RelatedSource, float] = {
    RelatedSource.SHARED_CHAR: 4.0,
    RelatedSource.ENCOUNTERED: 3.0,
    RelatedSource.SHARED_COMPONENT: 2.0,
    RelatedSource.SAME_LEVEL: 1.0,
}
TOP_POOL_FACTOR = 3  # chỉ bốc trong nhóm điểm cao nhất, kích thước = số cần chọn × hệ số này
DEFAULT_MAX_LEVEL = 3  # chưa khai báo trình độ thì không vượt quá HSK 3 (F09.09)
LEVEL_MARGIN = 1  # từ mở rộng được khó hơn trình độ tối đa 1 cấp


def is_dictionary_backed(hsk_level: int | None, dictionary_meaning: str | None) -> bool:
    """Từ đã lưu đủ tin cậy làm cầu nối: có cấp HSK hoặc có nghĩa trong từ điển (không phải từ rác do OCR)."""
    return hsk_level is not None or bool(short_meaning(dictionary_meaning))


def related_count(question_count: int) -> int:
    """Số câu từ mở rộng: làm tròn nửa lên của 15% (10 câu → 2, 5 câu → 1)."""
    return math.floor(question_count * RELATED_RATIO + 0.5)


def max_level_for(learner_level: int | None, bridge_level: int | None) -> int:
    """Cấp HSK tối đa của từ mở rộng gắn với một từ đã lưu.

    Đã khai báo trình độ: trình độ + 1. Chưa khai báo: cấp của từ đã lưu + 1, nhưng không quá HSK 3.
    """
    if learner_level is not None:
        return learner_level + LEVEL_MARGIN
    return min(DEFAULT_MAX_LEVEL, (bridge_level or 1) + LEVEL_MARGIN)


def candidate_score(candidate: RelatedCandidate) -> float:
    return sum(SOURCE_WEIGHTS[s] for s in {link.source for link in candidate.links})


def best_link(candidate: RelatedCandidate) -> RelatedLink:
    """Liên kết mạnh nhất, làm cầu nối `related_entry_id` và nội dung gợi ý."""
    return max(candidate.links, key=lambda link: SOURCE_WEIGHTS[link.source])


def pick_related(
    candidates: Sequence[RelatedCandidate], count: int, rng: random.Random
) -> list[RelatedCandidate]:
    """Bốc `count` từ không lặp, ngẫu nhiên có trọng số theo điểm trong nhóm điểm cao nhất."""
    pool = sorted(candidates, key=lambda c: (-candidate_score(c), c.term))[: max(count, 0) * TOP_POOL_FACTOR]
    chosen: list[RelatedCandidate] = []
    while pool and len(chosen) < count:
        picked = rng.choices(pool, weights=[candidate_score(c) for c in pool], k=1)[0]
        chosen.append(picked)
        pool.remove(picked)
    return chosen


def build_hint(candidate: RelatedCandidate) -> str:
    """Gợi ý không lộ đáp án: nói vì sao từ này liên quan tới từ người học đã lưu."""
    link = best_link(candidate)
    bridge = link.bridge_term
    meaning = short_meaning(link.bridge_meaning)
    bridge_text = f"{bridge} ({meaning})" if meaning else bridge
    if link.source is RelatedSource.SHARED_CHAR and link.detail and not is_common_char(link.detail):
        return f"Gợi ý: chữ {link.detail} giống trong {bridge_text} của bạn"
    if link.source is RelatedSource.ENCOUNTERED:
        where = link.detail or "khi đọc truyện"
        return f"Gợi ý: từ này bạn đã gặp ở {where}"
    if link.source is RelatedSource.SHARED_COMPONENT and link.detail:
        return f"Gợi ý: có chung thành phần {link.detail} với {bridge_text} của bạn"
    if candidate.han_viet:
        return f"Gợi ý: âm Hán Việt là {candidate.han_viet}"
    return f"Gợi ý: cùng cấp HSK với {bridge_text} của bạn"
