"""Quy tắc thuần của M10: gom từ trong chương và chấm điểm mức phù hợp (F10.01)."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Iterable, Mapping, Sequence

from app.modules.suggestions.domain.entities import (
    BubbleTokens,
    ScoredTerm,
    SeriesCandidate,
    SeriesRecommendation,
    TermStats,
)
from app.modules.suggestions.domain.errors import InvalidSuggestionTermError

MAX_TERM_CHARS = 32
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# Trọng số [Đề xuất] của F10.01 bước 4. Khi người học chưa khai báo trình độ HSK thì bỏ thành phần HSK và
# chia lại trọng số cho tần suất và số lần tra.
W_FREQ = 0.50
W_HSK = 0.35
W_LOOKUP = 0.15
W_FREQ_NO_LEVEL = 0.70
W_LOOKUP_NO_LEVEL = 0.30

HSK_UNKNOWN_FIT = 0.3  # từ không có cấp HSK: điểm phù hợp trung bình thấp
HSK_ABOVE_STEP = 0.2  # mỗi cấp vượt quá trình độ+1 giảm bấy nhiêu
HSK_ABOVE_FLOOR = 0.1
HSK_ONE_BELOW_FIT = 0.6
HSK_FAR_BELOW_FIT = 0.1  # thấp hơn trình độ từ 2 cấp: gần như đã biết
NO_LEVEL_HSK1_FACTOR = (
    0.5  # chưa khai báo trình độ: từ HSK 1 hầu như ai cũng biết nên giảm điểm để không chiếm đầu danh sách
)


def _is_han(ch: str) -> bool:
    code = ord(ch)
    return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x2FA1F


def normalize_term(raw: str) -> str:
    """NFKC, bỏ khoảng trắng hai đầu; chỉ gồm chữ Hán và dài tối đa `MAX_TERM_CHARS`."""
    term = unicodedata.normalize("NFKC", raw).strip()
    if not term or len(term) > MAX_TERM_CHARS or not all(_is_han(c) for c in term):
        raise InvalidSuggestionTermError()
    return term


def collect_stats(bubbles: Iterable[BubbleTokens]) -> dict[str, TermStats]:
    """Đếm tần suất từng từ (chỉ token toàn chữ Hán) và ghi lại lần xuất hiện đầu tiên.

    `bubbles` phải theo thứ tự đọc (trang rồi bong bóng) để "lần đầu" đúng nghĩa.
    """
    stats: dict[str, TermStats] = {}
    for bubble in bubbles:
        for token in bubble.tokens:
            if not isinstance(token, dict):
                continue
            word = token.get("word")
            if not isinstance(word, str) or not word or len(word) > MAX_TERM_CHARS:
                continue
            if not all(_is_han(c) for c in word):
                continue
            current = stats.get(word)
            if current is None:
                pinyin = token.get("pinyin")
                stats[word] = TermStats(
                    word, 1, bubble.page_id, bubble.page_no, bubble.bubble_id, str(pinyin) if pinyin else None
                )
            else:
                current.occurrences += 1
    return stats


def hsk_fit(term_level: int | None, learner_level: int) -> float:
    """Độ phù hợp 0..1: 1 khi cấp từ bằng trình độ hoặc cao hơn 1; giảm dần khi cao hơn nữa;
    từ thấp hơn trình độ 2 cấp trở lên (đã biết) giảm mạnh."""
    if term_level is None:
        return HSK_UNKNOWN_FIT
    gap = term_level - learner_level
    if gap in (0, 1):
        return 1.0
    if gap > 1:
        return max(HSK_ABOVE_FLOOR, 1.0 - HSK_ABOVE_STEP * (gap - 1))
    return HSK_ONE_BELOW_FIT if gap == -1 else HSK_FAR_BELOW_FIT


def _log_norm(value: int, maximum: int) -> float:
    return math.log1p(value) / math.log1p(maximum) if maximum > 0 else 0.0


def rank_terms(
    stats: Mapping[str, TermStats],
    lookups: Mapping[str, int],
    levels: Mapping[str, int | None],
    learner_level: int | None,
) -> list[ScoredTerm]:
    """Điểm = tần suất chuẩn hóa + độ phù hợp HSK + số lần tra chuẩn hóa; cao trước, hòa thì theo tần suất
    rồi theo thứ tự xuất hiện đầu tiên."""
    if not stats:
        return []
    max_occ = max(s.occurrences for s in stats.values())
    max_lookup = max((lookups.get(t, 0) for t in stats), default=0)
    scored: list[ScoredTerm] = []
    for term, s in stats.items():
        looked = lookups.get(term, 0)
        freq = _log_norm(s.occurrences, max_occ)
        look = _log_norm(looked, max_lookup)
        level = levels.get(term)
        if learner_level is None:
            score = W_FREQ_NO_LEVEL * freq + W_LOOKUP_NO_LEVEL * look
            if level == 1:
                score *= NO_LEVEL_HSK1_FACTOR
        else:
            score = W_FREQ * freq + W_HSK * hsk_fit(level, learner_level) + W_LOOKUP * look
        scored.append(ScoredTerm(s, looked, level, round(score, 4)))
    # sorted ổn định nên thứ tự gốc (lần xuất hiện đầu tiên) giữ nguyên khi điểm và tần suất bằng nhau
    return sorted(scored, key=lambda t: (-t.score, -t.stats.occurrences))


def reduplication_root(term: str) -> str | None:
    """Từ gốc của dạng lặp: AA -> A (看看 -> 看), ABAB -> AB; None nếu không phải dạng lặp."""
    size = len(term)
    if size in (2, 4) and term[: size // 2] == term[size // 2 :]:
        return term[: size // 2]
    return None


def fold_reduplication(
    stats: Mapping[str, TermStats], known_roots: Sequence[str] | set[str]
) -> dict[str, TermStats]:
    """Gộp dạng lặp về từ gốc khi đếm, chỉ với từ gốc có trong từ điển (`known_roots`).

    Lần xuất hiện đầu tiên của từ gốc giữ nguyên nếu có sẵn; nếu từ gốc chưa có riêng thì lấy vị trí của dạng
    lặp (pinyin của dạng lặp không dùng lại vì đọc khác).
    """
    merged: dict[str, TermStats] = {}
    folded: list[tuple[str, TermStats]] = []
    for term, s in stats.items():
        root = reduplication_root(term)
        if root is not None and root in known_roots:
            folded.append((root, s))
        else:
            merged[term] = s
    for root, s in folded:
        existing = merged.get(root)
        if existing is None:
            merged[root] = TermStats(root, s.occurrences, s.page_id, s.page_no, s.bubble_id, None)
        else:
            merged[root] = TermStats(
                root,
                existing.occurrences + s.occurrences,
                existing.page_id,
                existing.page_no,
                existing.bubble_id,
                existing.pinyin,
            )
    return merged


# --- F10.04: gợi ý truyện theo trình độ --------------------------------------------------------------
RECOMMEND_DEFAULT = 3
RECOMMEND_MAX = 3  # SRS: gợi ý 1 đến 3 truyện
RECOMMEND_LEVEL_MARGIN = 1  # truyện có cấp ước tính bằng trình độ hoặc cao hơn 1 cấp
POPULAR_MAX_LEVEL = 3  # chưa khai báo trình độ: gợi ý truyện phổ biến có cấp HSK thấp


def level_window(learner_level: int | None) -> tuple[int, int]:
    """Khoảng cấp HSK ước tính của truyện được gợi ý."""
    if learner_level is None:
        return 1, POPULAR_MAX_LEVEL
    return learner_level, learner_level + RECOMMEND_LEVEL_MARGIN


def _reason(candidate: SeriesCandidate, learner_level: int | None) -> str:
    if learner_level is None:
        reason = "Được nhiều người thêm vào Thư viện, cấp HSK thấp"
    elif candidate.est_hsk_level == learner_level:
        reason = f"Đúng trình độ HSK {learner_level} của bạn"
    else:
        reason = f"Cao hơn trình độ của bạn một cấp (HSK {candidate.est_hsk_level}), vừa sức để tiến bộ"
    if candidate.finished:
        return f"{reason} · bạn đã đọc xong"
    return f"{reason} · đã có trong Thư viện" if candidate.in_library else reason


def recommend_series(
    candidates: Iterable[SeriesCandidate], learner_level: int | None, limit: int
) -> list[SeriesRecommendation]:
    """Chọn tối đa `limit` truyện: truyện chưa thêm vào Thư viện và chưa đọc xong trước, rồi theo điểm đánh
    giá giảm dần (chưa khai báo trình độ thì theo độ phổ biến trước); hòa thì theo mã truyện."""
    low, high = level_window(learner_level)
    pool = [c for c in candidates if c.est_hsk_level is not None and low <= c.est_hsk_level <= high]

    def key(c: SeriesCandidate) -> tuple[int, int, float, int, int]:
        seen = int(c.in_library or c.finished)
        popularity = -c.library_count if learner_level is None else 0
        return seen, popularity, -(c.rating_avg or 0.0), -c.rating_count, c.series_id

    ranked = sorted(pool, key=key)[: max(limit, 0)]
    return [SeriesRecommendation(c, _reason(c, learner_level)) for c in ranked]


# --- F10.05: độ phủ từ vựng của chương ---------------------------------------------------------------
COVERAGE_READY = "ready"
COVERAGE_PROCESSING = "processing"  # còn trang chưa xong: kết quả tạm tính
COVERAGE_EMPTY = "empty"  # chưa có trang xong hoặc không có từ ở cấp phù hợp: không hiển thị 0/0


def coverage_percent(known: int, total: int) -> int:
    return round(known * 100 / total) if total > 0 else 0


def coverage_status(processing: bool, total: int) -> str:
    if total == 0:
        return COVERAGE_EMPTY
    return COVERAGE_PROCESSING if processing else COVERAGE_READY
