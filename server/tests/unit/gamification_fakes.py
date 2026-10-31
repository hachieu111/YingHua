"""Bản giả (trong bộ nhớ) của các kho M16 cho test đơn vị: sổ XP, bộ đếm ngày, ví, huy hiệu, mùa."""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.modules.gamification.application.dto import (
    BadgeView,
    DayCounters,
    LeaderboardEntry,
    LeaderboardTotals,
    RankedScore,
    UserProfile,
)
from app.modules.gamification.domain.entities import (
    Achievement,
    AchievementMetric,
    AchievementSource,
    BladeBest,
    CharRow,
    HanziRadicalInfo,
    MinigameRound,
    MinigameSession,
    NewMinigameSession,
    NewXpEvent,
    Season,
    SeasonResult,
    SeasonResultRow,
    SeasonStatus,
    UserAchievement,
    WordRow,
    XpSource,
)
from app.modules.gamification.domain.minigame_rules import WeakRadical
from app.modules.gamification.domain.season_rules import vn_date
from app.modules.gamification.domain.xp_rules import ACTIVITY_SOURCES
from app.modules.rewards.application.public import GrantResult, LedgerReason, RewardBundle, WalletSnapshot

DEFAULT_TZ = "Asia/Ho_Chi_Minh"


class FakeXp:
    def __init__(self) -> None:
        self.rows: dict[tuple[int, XpSource, str], NewXpEvent] = {}

    async def lock_user(self, user_id: int) -> None:
        return None

    async def exists(self, user_id: int, source: XpSource, source_ref: str) -> bool:
        return (user_id, source, source_ref) in self.rows

    async def insert_if_absent(self, event: NewXpEvent) -> bool:
        key = (event.user_id, event.source, event.source_ref)
        if key in self.rows:
            return False
        self.rows[key] = event
        return True

    def _of(self, user_id: int) -> list[NewXpEvent]:
        return [e for (uid, _, _), e in self.rows.items() if uid == user_id]

    async def count_for_day(self, user_id: int, day: date, source: XpSource) -> int:
        return sum(1 for e in self._of(user_id) if e.activity_date == day and e.source is source)

    async def activity_xp_for_day(self, user_id: int, day: date) -> int:
        return sum(
            e.amount for e in self._of(user_id) if e.activity_date == day and e.source in ACTIVITY_SOURCES
        )

    async def rewarded_at(self, user_id: int, source: XpSource, refs: Sequence[str]) -> dict[str, datetime]:
        return {
            e.source_ref: e.created_at
            for e in self._of(user_id)
            if e.source is source and e.source_ref in refs
        }

    async def xp_for_day(self, user_id: int, day: date) -> int:
        return sum(e.amount for e in self._of(user_id) if e.activity_date == day)

    async def xp_between(self, user_id: int, start_at: datetime, end_at: datetime) -> int:
        return sum(e.amount for e in self._of(user_id) if start_at <= e.created_at < end_at)

    async def xp_total(self, user_id: int) -> int:
        return sum(e.amount for e in self._of(user_id))

    async def xp_by_vn_day(self, user_id: int, start_at: datetime, end_at: datetime) -> dict[date, int]:
        out: dict[date, int] = {}
        for e in self._of(user_id):
            if start_at <= e.created_at < end_at:
                out[vn_date(e.created_at)] = out.get(vn_date(e.created_at), 0) + e.amount
        return out


class FakeActivityReader:
    def __init__(self) -> None:
        self.days: dict[tuple[int, date], list[int]] = {}

    def add(self, user_id: int, day: date, pages: int = 0, reviews: int = 0) -> None:
        row = self.days.setdefault((user_id, day), [0, 0])
        row[0] += pages
        row[1] += reviews

    async def day_counters(self, user_id: int, day: date) -> DayCounters:
        pages, reviews = self.days.get((user_id, day), [0, 0])
        return DayCounters(pages, reviews)

    async def pages_between(self, user_id: int, start: date, end: date) -> int:
        return sum(v[0] for (uid, d), v in self.days.items() if uid == user_id and start <= d <= end)

    async def study_days(self, user_id: int) -> list[date]:
        return sorted(d for (uid, d), v in self.days.items() if uid == user_id and v[0] + v[1] > 0)


class FakeUsers:
    def __init__(self) -> None:
        self.profiles: dict[int, UserProfile] = {}

    def set(self, user_id: int, **changes: Any) -> None:
        base = UserProfile(user_id, DEFAULT_TZ, None, None, True, display_name=f"Người học {user_id}")
        self.profiles[user_id] = dataclasses.replace(base, **changes)

    async def profile(self, user_id: int) -> UserProfile:
        if user_id not in self.profiles:
            self.set(user_id)
        return self.profiles[user_id]


class FakeRewards:
    """Ghi lại các lần trao; gói có xu/vé/VIP chống trùng theo khóa như M17, gói chỉ có khung thì không."""

    def __init__(self) -> None:
        self.grants: list[tuple[int, RewardBundle, str, LedgerReason | None]] = []
        self._keys: set[tuple[int, str, str]] = set()
        self.fail_for: set[int] = set()

    async def grant(
        self, user_id: int, bundle: RewardBundle, key: str, reason: LedgerReason | None, now: datetime
    ) -> GrantResult:
        if user_id in self.fail_for:
            raise RuntimeError("Lỗi giả khi trao thưởng")
        snapshot = WalletSnapshot(user_id, 0, 0, None, None)
        if bundle.has_currency:
            currencies = [
                name
                for name, amount in (
                    ("coin", bundle.coins),
                    ("ticket", bundle.tickets),
                    ("vip", bundle.vip_days),
                )
                if amount
            ]
            fresh = [c for c in currencies if (user_id, key, c) not in self._keys]
            if not fresh:
                return GrantResult(snapshot, [], True)
            self._keys.update((user_id, key, c) for c in fresh)
        self.grants.append((user_id, bundle, key, reason))
        return GrantResult(snapshot)

    async def decorations(self, user_ids: Sequence[int], now: datetime) -> dict[int, Any]:
        return {}

    def coins_for(self, user_id: int) -> int:
        return sum(b.coins for uid, b, _, _ in self.grants if uid == user_id)

    def keys_for(self, user_id: int) -> list[str]:
        return [k for uid, _, k, _ in self.grants if uid == user_id]


def default_achievements() -> list[Achievement]:
    """Bảy huy hiệu khởi tạo của migration 0012."""
    spec = [
        ("sakura_member", AchievementMetric.STUDY_DAYS, (30, 100, 365), (50, 100, 200)),
        ("top_scholar", AchievementMetric.SEASON_TOP3, (1,), (0,)),
        ("manhua_elite", AchievementMetric.PAGES_READ, (100, 500, 2000), (50, 100, 200)),
        ("seed_sower", AchievementMetric.WORDS_SAVED, (300, 1000, 3000), (50, 100, 200)),
        ("hsk3_master", AchievementMetric.HSK3_MASTERED, (300,), (200,)),
        ("night_owl", AchievementMetric.NIGHT_PAGES, (50, 200, 500), (50, 100, 200)),
        ("apprentice_translator", AchievementMetric.BUBBLE_LOOKUPS, (150, 500, 1500), (50, 100, 200)),
    ]
    return [
        Achievement(i + 1, code, code.replace("_", " ").title(), "mô tả", metric, th, coins, "star", i + 1)
        for i, (code, metric, th, coins) in enumerate(spec)
    ]


class FakeAchievements:
    def __init__(self) -> None:
        self.definitions = default_achievements()
        self.rows: dict[tuple[int, int], UserAchievement] = {}

    async def list_active(self) -> list[Achievement]:
        return list(self.definitions)

    async def get_by_code(self, code: str) -> Achievement | None:
        return next((a for a in self.definitions if a.code == code), None)

    async def user_rows(self, user_id: int) -> dict[int, UserAchievement]:
        return {aid: r for (uid, aid), r in self.rows.items() if uid == user_id}

    async def upsert_tier(
        self, user_id: int, achievement_id: int, tier: int, source: AchievementSource, now: datetime
    ) -> None:
        current = self.rows.get((user_id, achievement_id))
        if current is None:
            self.rows[(user_id, achievement_id)] = UserAchievement(
                user_id, achievement_id, tier, source, False, now, now
            )
        elif tier > current.tier:
            self.rows[(user_id, achievement_id)] = dataclasses.replace(
                current, tier=tier, tier_reached_at=now
            )

    async def equipped_for(self, user_ids: Sequence[int]) -> dict[int, BadgeView]:
        out: dict[int, BadgeView] = {}
        for (uid, aid), row in self.rows.items():
            if uid in user_ids and row.is_equipped:
                a = next(x for x in self.definitions if x.id == aid)
                out[uid] = BadgeView(a.code, a.name, row.tier, a.style_key)
        return out

    async def set_equipped(self, user_id: int, achievement_id: int | None) -> None:
        for key, row in list(self.rows.items()):
            if key[0] == user_id:
                self.rows[key] = dataclasses.replace(row, is_equipped=key[1] == achievement_id)


class FakeMetrics:
    def __init__(self) -> None:
        self.data: dict[AchievementMetric, int] = {}

    async def values(
        self, user_id: int, metrics: Iterable[AchievementMetric], timezone: str
    ) -> dict[AchievementMetric, int]:
        return {m: self.data.get(m, 0) for m in metrics}

    async def active_users(self, since: datetime, after_user_id: int, limit: int) -> list[int]:
        return []


class FakeSeasons:
    def __init__(self) -> None:
        self.seasons: dict[int, Season] = {}
        self.results: dict[tuple[int, int], SeasonResult] = {}
        self.missing: list[datetime] = []

    async def get_containing(self, at: datetime) -> Season | None:
        return next((s for s in self.seasons.values() if s.starts_at <= at < s.ends_at), None)

    async def ensure(self, starts_at: datetime, ends_at: datetime, now: datetime) -> tuple[Season, bool]:
        existing = next((s for s in self.seasons.values() if s.starts_at == starts_at), None)
        if existing:
            return existing, False
        season = Season(len(self.seasons) + 1, len(self.seasons) + 1, starts_at, ends_at, SeasonStatus.ACTIVE)
        self.seasons[season.id] = season
        return season, True

    async def missing_week_starts(self, since: datetime, until: datetime) -> list[datetime]:
        return [m for m in self.missing if not any(s.starts_at == m for s in self.seasons.values())]

    async def has_unfinished_ended(self, now: datetime) -> bool:
        return any(s.status is not SeasonStatus.FINALIZED and s.ends_at <= now for s in self.seasons.values())

    async def claim_ended(self, now: datetime, exclude_ids: Sequence[int]) -> Season | None:
        open_ones = [
            s
            for s in sorted(self.seasons.values(), key=lambda x: x.ends_at)
            if s.status is not SeasonStatus.FINALIZED and s.ends_at <= now and s.id not in exclude_ids
        ]
        return open_ones[0] if open_ones else None

    async def set_status(self, season_id: int, status: SeasonStatus, finalized_at: datetime | None) -> None:
        self.seasons[season_id] = dataclasses.replace(
            self.seasons[season_id], status=status, finalized_at=finalized_at
        )

    async def add_results(self, results: Sequence[SeasonResult], now: datetime) -> None:
        for r in results:
            self.results.setdefault((r.season_id, r.user_id), r)

    async def claim_pending_result(self, season_id: int, skip_users: Sequence[int]) -> SeasonResult | None:
        pending = sorted(
            (
                r
                for r in self.results.values()
                if r.season_id == season_id and r.reward_granted_at is None and r.user_id not in skip_users
            ),
            key=lambda r: r.rank,
        )
        return pending[0] if pending else None

    async def mark_granted(self, season_id: int, user_id: int, at: datetime) -> None:
        key = (season_id, user_id)
        self.results[key] = dataclasses.replace(self.results[key], reward_granted_at=at)

    async def count_pending(self, season_id: int) -> int:
        return sum(
            1 for r in self.results.values() if r.season_id == season_id and r.reward_granted_at is None
        )

    async def results_of_user(
        self, user_id: int, offset: int, limit: int
    ) -> tuple[list[SeasonResultRow], int]:
        rows = [
            SeasonResultRow(r, self.seasons[r.season_id])
            for r in self.results.values()
            if r.user_id == user_id
        ]
        return rows[offset : offset + limit], len(rows)

    async def result_of_user(self, season_id: int, user_id: int) -> SeasonResult | None:
        return self.results.get((season_id, user_id))


class FakeLeaderboard:
    def __init__(self) -> None:
        self.ranking: list[RankedScore] = []
        self.entries: list[LeaderboardEntry] = []

    async def top_exp(self, window: Any, limit: int, min_xp: int) -> list[RankedScore]:
        return [r for r in self.ranking if r.score >= min_xp][:limit]

    async def page(
        self, metric: Any, window: Any, offset: int, limit: int
    ) -> tuple[list[LeaderboardEntry], int]:
        return self.entries[offset : offset + limit], len(self.entries)

    async def rank_of(self, metric: Any, window: Any, user_id: int) -> RankedScore | None:
        return next(
            (RankedScore(e.user_id, e.rank, e.score) for e in self.entries if e.user_id == user_id), None
        )

    async def score_at_rank(self, metric: Any, window: Any, rank: int) -> int | None:
        return next((e.score for e in self.entries if e.rank == rank), None)

    async def totals(self, window: Any, season_window: Any) -> LeaderboardTotals:
        return LeaderboardTotals(len(self.entries), 0, sum(e.score for e in self.entries))


class FakeMinigames:
    def __init__(self) -> None:
        self.sessions: list[MinigameSession] = []
        self.rows: list[NewMinigameSession] = []
        self.rounds: dict[uuid.UUID, MinigameRound] = {}

    async def add_round(self, round_: MinigameRound) -> None:
        self.rounds[round_.id] = round_

    async def get_round_for_update(self, round_id: uuid.UUID, user_id: int) -> MinigameRound | None:
        found = self.rounds.get(round_id)
        return found if found is not None and found.user_id == user_id else None

    async def purge_rounds_before(self, cutoff: datetime, limit: int) -> int:
        old = sorted((r for r in self.rounds.values() if r.issued_at < cutoff), key=lambda r: r.issued_at)
        for found in old[:limit]:
            del self.rounds[found.id]
        return len(old[:limit])

    async def mark_round_submitted(self, round_id: uuid.UUID, now: datetime) -> bool:
        found = self.rounds[round_id]
        if found.submitted_at is not None:
            return False
        self.rounds[round_id] = dataclasses.replace(found, submitted_at=now)
        return True

    async def add(self, session: NewMinigameSession) -> MinigameSession:
        self.rows.append(session)
        saved = MinigameSession(len(self.rows), session.user_id, session.score)
        self.sessions.append(saved)
        return saved

    async def best_score(self, user_id: int, hsk_band: int | None) -> int:
        return max((r.score for r in self.rows if r.user_id == user_id and r.hsk_band == hsk_band), default=0)

    async def best_records(self, user_id: int) -> list[BladeBest]:
        bands = {r.hsk_band for r in self.rows if r.user_id == user_id}
        found: list[BladeBest] = []
        for band in sorted(bands, key=lambda b: (b is None, b or 0)):
            mine = [r for r in self.rows if r.user_id == user_id and r.hsk_band == band]
            mode = "weak_radical" if band is None else "hsk"
            found.append(
                BladeBest(mode, band, max(r.score for r in mine), max(r.max_combo for r in mine), len(mine))
            )
        return found


class FakeChars:
    """Bảng `hanzi` giả: chữ -> (bộ thủ, thành phần)."""

    def __init__(self) -> None:
        self.infos: dict[str, HanziRadicalInfo] = {}
        self.weak_counts: dict[str, int] = {}
        self.common: list[WeakRadical] = []
        self.char_rows: list[CharRow] = []
        self.word_rows: list[WordRow] = []

    def add(self, ch: str, radical: str | None, components: tuple[str, ...] = ()) -> None:
        self.infos[ch] = HanziRadicalInfo(ch, radical, components, "pin")

    async def weak_char_counts(self, user_id: int, since: datetime) -> dict[str, int]:
        return dict(self.weak_counts)

    async def hanzi_infos(self, chars: Iterable[str]) -> dict[str, HanziRadicalInfo]:
        return {c: self.infos[c] for c in chars if c in self.infos}

    async def band_chars(self, band: int, limit: int) -> list[CharRow]:
        return self.char_rows[:limit]

    async def band_words(self, band: int, limit: int) -> list[WordRow]:
        return self.word_rows[:limit]

    async def radical_chars(self, user_id: int, radical: str, max_hsk: int, limit: int) -> list[CharRow]:
        return self.char_rows[:limit]

    async def radical_words(self, radical: str, max_hsk: int, limit: int) -> list[WordRow]:
        return self.word_rows[:limit]

    async def common_radicals(self, max_hsk: int, limit: int) -> list[WeakRadical]:
        return self.common[:limit]


class FakeGamification:
    """Một "giao dịch" giả dùng chung dữ liệu giữa các lần `async with` (cho use case nhiều giao dịch)."""

    def __init__(self) -> None:
        self.xp = FakeXp()
        self.activity = FakeActivityReader()
        self.users = FakeUsers()
        self.rewards = FakeRewards()
        self.achievements = FakeAchievements()
        self.metrics = FakeMetrics()
        self.seasons = FakeSeasons()
        self.leaderboard = FakeLeaderboard()
        self.minigames = FakeMinigames()
        self.chars = FakeChars()
        self.commits = 0

    async def __aenter__(self) -> FakeGamification:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def days_before(day: date, n: int) -> date:
    return day - timedelta(days=n)
