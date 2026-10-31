"""Thực thể của M16 Gamification - thuần Python, không phụ thuộc framework."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class XpSource(str, Enum):
    """Nguồn của một sự kiện XP (khớp CHECK của `xp_events.source`)."""

    PAGE_READ = "page_read"
    REVIEW = "review"
    WORD_SAVED = "word_saved"
    QUIZ = "quiz"
    MINIGAME = "minigame"
    QUEST = "quest"
    WEEKLY_GOAL = "weekly_goal"
    STREAK_MILESTONE = "streak_milestone"


class SeasonStatus(str, Enum):
    ACTIVE = "active"
    FINALIZING = "finalizing"
    FINALIZED = "finalized"


class SeasonTier(str, Enum):
    TOP3 = "top3"
    TOP10 = "top10"
    TOP50 = "top50"


class AchievementMetric(str, Enum):
    STUDY_DAYS = "study_days"
    PAGES_READ = "pages_read"
    WORDS_SAVED = "words_saved"
    HSK3_MASTERED = "hsk3_mastered"
    NIGHT_PAGES = "night_pages"
    BUBBLE_LOOKUPS = "bubble_lookups"
    SEASON_TOP3 = "season_top3"


class AchievementSource(str, Enum):
    RULE = "rule"
    SEASON = "season"


class LeaderboardMetric(str, Enum):
    EXP = "exp"
    VOCAB = "vocab"
    PAGES = "pages"
    STREAK = "streak"


class LeaderboardPeriod(str, Enum):
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class NewXpEvent:
    user_id: int
    source: XpSource
    source_ref: str
    amount: int
    capped: bool
    activity_date: date
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Season:
    id: int
    number: int
    starts_at: datetime
    ends_at: datetime
    status: SeasonStatus
    finalized_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SeasonResult:
    season_id: int
    user_id: int
    rank: int
    xp: int
    tier: SeasonTier
    reward_granted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SeasonResultRow:
    """Kết quả mùa của một người kèm thông tin mùa (lịch sử mùa của tôi, F16.09)."""

    result: SeasonResult
    season: Season


@dataclass(frozen=True, slots=True)
class Achievement:
    id: int
    code: str
    name: str
    description: str
    metric: AchievementMetric
    thresholds: tuple[int, ...]
    coin_rewards: tuple[int, ...]
    style_key: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class UserAchievement:
    user_id: int
    achievement_id: int
    tier: int
    source: AchievementSource
    is_equipped: bool
    unlocked_at: datetime
    tier_reached_at: datetime


@dataclass(frozen=True, slots=True)
class BladeItem:
    """Một mục của ván "Gõ pinyin chém chữ": chữ hoặc từ boss kèm mọi đáp án chấp nhận (a-z, không dấu)."""

    index: int
    text: str
    pinyin: str
    answers: tuple[str, ...]
    han_viet: str | None
    hsk_level: int | None
    is_boss: bool

    @property
    def min_keys(self) -> int:
        """Số phím ít nhất để gõ đúng mục này (đáp án ngắn nhất)."""
        return min(len(a) for a in self.answers)


@dataclass(frozen=True, slots=True)
class CharRow:
    """Chữ lấy từ `hanzi` (+ cấp HSK thấp nhất của từ chứa chữ) trước khi dựng đáp án."""

    ch: str
    pinyin: str | None
    han_viet: str | None
    hsk_level: int | None


@dataclass(frozen=True, slots=True)
class WordRow:
    """Từ hai chữ lấy từ `hsk_words`, dùng làm boss."""

    word: str
    pinyin: str | None
    hsk_level: int | None


@dataclass(frozen=True, slots=True)
class BladeBest:
    """Kỷ lục của một người theo chế độ và cấp HSK (`hsk_band` rỗng: chế độ bộ thủ yếu)."""

    mode: str
    hsk_band: int | None
    best_score: int
    best_combo: int
    plays: int


@dataclass(frozen=True, slots=True)
class MinigameSession:
    id: int
    user_id: int
    score: int


@dataclass(frozen=True, slots=True)
class NewMinigameSession:
    user_id: int
    hsk_band: int | None
    target_radical: str | None
    score: int
    correct: int
    wrong: int
    typos: int
    max_combo: int
    duration_ms: int
    played_at: datetime


@dataclass(frozen=True, slots=True)
class MinigameRound:
    """Lượt chơi do máy chủ phát (F16.01): bộ mục đã phát kèm đáp án, nộp được đúng một lần."""

    id: uuid.UUID
    user_id: int
    mode: str
    hsk_band: int | None
    radical: str | None
    items: list[BladeItem]
    issued_at: datetime
    submitted_at: datetime | None


@dataclass(frozen=True, slots=True)
class HanziRadicalInfo:
    """Bộ thủ và thành phần của một chữ Hán (dữ liệu `hanzi`, F06.05)."""

    ch: str
    radical: str | None
    components: tuple[str, ...]
    pinyin: str | None = None

    def contains(self, target: str) -> bool:
        return self.radical == target or target in self.components

    @property
    def parts(self) -> frozenset[str]:
        found = set(self.components)
        if self.radical:
            found.add(self.radical)
        return frozenset(found)
