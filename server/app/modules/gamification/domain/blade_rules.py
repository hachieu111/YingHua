"""Luật mini-game "Gõ pinyin chém chữ" (F16.01): dựng bộ mục, chấm lại kết quả ở máy chủ. Hàm thuần."""

from __future__ import annotations

import dataclasses
import random
from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.gamification.domain.entities import BladeItem, CharRow, WordRow
from app.modules.gamification.domain.errors import (
    InvalidMinigameRequestError,
    InvalidMinigameResultError,
    NotEnoughCharsForGameError,
)
from app.modules.gamification.domain.pinyin_answers import char_answers, word_answers

MODE_HSK = "hsk"
MODE_WEAK_RADICAL = "weak_radical"
MIN_BAND, MAX_BAND = 1, 7  # cấp 7 gộp HSK 7-9
LAST_SINGLE_LEVEL = 7
MAX_LEVEL_IN_LAST_BAND = 9

ITEMS_PER_ROUND = 100
MIN_ITEMS_PER_ROUND = 20
BOSS_EVERY = 10  # khoảng 1/10 mục là từ boss hai chữ
LIVES = 3
HIT_POINTS = 10
BOSS_MULTIPLIER = 3
COMBO_STEP = 5  # mỗi chừng này hit liên tiếp tăng thêm một nấc nhân
COMBO_HALVES_PER_STEP = 1  # mỗi nấc thêm 0,5 (tính theo nửa đơn vị để dùng số nguyên)
MAX_COMBO_HALVES = 6  # trần nhân x3
LIFE_BONUS = 5  # điểm thưởng mỗi mạng còn lại khi hết bộ mục
MAX_SCORE = 32767  # SMALLINT
MIN_KEY_MS = 35  # khoảng cách tối thiểu cho mỗi phím giữa hai hit, chống bot
MAX_EVENTS = 300
MAX_TYPOS = 2000
MS_TOLERANCE = 5000
MAX_MISSED_SHOWN = 20
RANK_THRESHOLDS: tuple[tuple[str, int, float], ...] = (
    ("S", 80, 0.95),
    ("A", 50, 0.90),
    ("B", 25, 0.80),
)
LOWEST_RANK = "C"


def band_levels(band: int) -> tuple[int, int]:
    """Khoảng cấp `hsk_words.level` của một cấp chơi; cấp 7 gồm HSK 7-9."""
    return (band, MAX_LEVEL_IN_LAST_BAND if band == MAX_BAND else band)


def validate_round_request(mode: str, hsk_band: int | None, radical: str | None) -> None:
    if mode == MODE_HSK and hsk_band is not None and MIN_BAND <= hsk_band <= MAX_BAND:
        return
    if mode == MODE_WEAK_RADICAL and radical:
        return
    raise InvalidMinigameRequestError()


def _char_item(row: CharRow) -> BladeItem | None:
    answers = char_answers(row.pinyin)
    if not answers or row.pinyin is None:
        return None
    level = None if row.hsk_level is None else min(row.hsk_level, LAST_SINGLE_LEVEL)
    return BladeItem(0, row.ch, row.pinyin, tuple(answers), row.han_viet, level, False)


def _boss_item(row: WordRow) -> BladeItem | None:
    answers = word_answers(row.pinyin)
    if not answers or row.pinyin is None:
        return None
    level = None if row.hsk_level is None else min(row.hsk_level, LAST_SINGLE_LEVEL)
    return BladeItem(0, row.word, row.pinyin, tuple(answers), None, level, True)


def build_items(chars: Sequence[CharRow], words: Sequence[WordRow], rng: random.Random) -> list[BladeItem]:
    """Dựng bộ mục: chữ đầu danh sách được ưu tiên, boss tối đa 1/10, xáo trộn; chỉ lặp chữ khi thiếu dữ liệu.

    Mục không dựng được đáp án a-z bị bỏ. Ít hơn `MIN_ITEMS_PER_ROUND` mục khác nhau → không chơi được.
    """
    normals = list({i.text: i for r in chars if (i := _char_item(r))}.values())
    boss_cap = ITEMS_PER_ROUND // BOSS_EVERY
    bosses = list({i.text: i for r in words if (i := _boss_item(r))}.values())[:boss_cap]
    if not normals or len(normals) + len(bosses) < MIN_ITEMS_PER_ROUND:
        raise NotEnoughCharsForGameError()
    picked = [normals[i % len(normals)] for i in range(ITEMS_PER_ROUND - len(bosses))]
    mixed = picked + bosses
    rng.shuffle(mixed)
    return [dataclasses.replace(item, index=i) for i, item in enumerate(mixed)]


@dataclass(frozen=True, slots=True)
class BladeEvent:
    index: int
    hit: bool
    ms: int


@dataclass(frozen=True, slots=True)
class BladeScore:
    score: int
    hits: int
    misses: int
    max_combo: int
    lives_left: int
    accuracy: float
    rank: str
    missed: tuple[BladeItem, ...]


def _combo_multiplier_halves(combo: int) -> int:
    return min(MAX_COMBO_HALVES, 2 + COMBO_HALVES_PER_STEP * (combo // COMBO_STEP))


def _check_events(items: Sequence[BladeItem], events: Sequence[BladeEvent], elapsed_ms: int) -> None:
    """Kiểm tính hợp lý của chuỗi sự kiện; sai là 400 `INVALID_MINIGAME_RESULT`."""
    if len(events) > MAX_EVENTS:
        raise InvalidMinigameResultError("Quá nhiều sự kiện trong một ván")
    seen: set[int] = set()
    last_ms = 0
    last_hit_ms = 0
    lives = LIVES
    for event in events:
        if not 0 <= event.index < len(items) or event.index in seen:
            raise InvalidMinigameResultError("Mục không có trong ván hoặc bị lặp")
        seen.add(event.index)
        if event.ms < last_ms or event.ms > elapsed_ms + MS_TOLERANCE:
            raise InvalidMinigameResultError("Mốc thời gian của sự kiện không hợp lệ")
        last_ms = event.ms
        if lives <= 0:
            raise InvalidMinigameResultError("Có sự kiện sau khi đã hết mạng")
        if not event.hit:
            lives -= 1
            continue
        if event.ms - last_hit_ms < items[event.index].min_keys * MIN_KEY_MS:
            raise InvalidMinigameResultError("Gõ nhanh hơn mức người chơi có thể")
        last_hit_ms = event.ms


def _rank(hits: int, accuracy: float) -> str:
    for name, min_hits, min_accuracy in RANK_THRESHOLDS:
        if hits >= min_hits and accuracy >= min_accuracy:
            return name
    return LOWEST_RANK


def score_blade(
    items: Sequence[BladeItem], events: Sequence[BladeEvent], typos: int, elapsed_ms: int
) -> BladeScore:
    """Chấm lại ván từ chuỗi sự kiện, không tin điểm do trình duyệt báo.

    Mỗi hit 10 điểm (boss x3) nhân hệ số combo 1 + 0,5 x (combo // 5) tối đa x3, combo tính cả hit hiện tại;
    `miss` đặt combo về 0 và mất một mạng; hết bộ mục còn mạng thì thưởng thêm mỗi mạng 5 điểm.
    Độ chính xác = phím đúng (độ dài đáp án ngắn nhất của các hit) / (phím đúng + gõ sai).
    """
    if not 0 <= typos <= MAX_TYPOS:
        raise InvalidMinigameResultError("Số lần gõ sai không hợp lệ")
    _check_events(items, events, elapsed_ms)
    score = combo = max_combo = hits = misses = correct_keys = 0
    missed: list[BladeItem] = []
    for event in events:
        item = items[event.index]
        if not event.hit:
            misses += 1
            combo = 0
            missed.append(item)
            continue
        hits += 1
        combo += 1
        max_combo = max(max_combo, combo)
        correct_keys += item.min_keys
        base = HIT_POINTS * (BOSS_MULTIPLIER if item.is_boss else 1)
        score += base * _combo_multiplier_halves(combo) // 2
    lives_left = max(0, LIVES - misses)
    if len(events) == len(items):
        score += LIFE_BONUS * lives_left
    total_keys = correct_keys + typos
    accuracy = round(correct_keys / total_keys, 4) if total_keys else 0.0
    return BladeScore(
        min(score, MAX_SCORE),
        hits,
        misses,
        max_combo,
        lives_left,
        accuracy,
        _rank(hits, accuracy),
        tuple(missed[:MAX_MISSED_SHOWN]),
    )
