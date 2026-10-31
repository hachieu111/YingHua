"""Giao diện (port) mà tầng hạ tầng của M16 phải hiện thực."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from typing import Any, Protocol

from app.modules.gamification.application.dto import (
    BadgeView,
    DayCounters,
    LeaderboardEntry,
    LeaderboardTotals,
    Notice,
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
    LeaderboardMetric,
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
from app.modules.gamification.domain.season_rules import LeaderboardWindow
from app.modules.rewards.application.public import Decoration, GrantResult, LedgerReason, RewardBundle


class XpRepository(Protocol):
    async def lock_user(self, user_id: int) -> None:
        """Khóa tư vấn theo người dùng tới hết giao dịch, để hai yêu cầu cùng lúc không vượt trần."""
        ...

    async def exists(self, user_id: int, source: XpSource, source_ref: str) -> bool: ...

    async def insert_if_absent(self, event: NewXpEvent) -> bool:
        """`INSERT ... ON CONFLICT DO NOTHING`. True nếu thật sự thêm dòng mới."""
        ...

    async def count_for_day(self, user_id: int, day: date, source: XpSource) -> int: ...

    async def activity_xp_for_day(self, user_id: int, day: date) -> int:
        """Tổng XP của các nguồn tính vào trần chung trong ngày hoạt động."""
        ...

    async def rewarded_at(self, user_id: int, source: XpSource, refs: Sequence[str]) -> dict[str, datetime]:
        """Thời điểm ghi của những mã tham chiếu đã có sự kiện."""
        ...

    async def xp_for_day(self, user_id: int, day: date) -> int:
        """Tổng XP theo ngày hoạt động của người học (viên "+n XP")."""
        ...

    async def xp_between(self, user_id: int, start_at: datetime, end_at: datetime) -> int: ...

    async def xp_total(self, user_id: int) -> int: ...

    async def xp_by_vn_day(self, user_id: int, start_at: datetime, end_at: datetime) -> dict[date, int]:
        """XP theo ngày giờ Việt Nam trong [start_at, end_at) (biểu đồ tuần, F16.03)."""
        ...


class ActivityReader(Protocol):
    """Đọc bộ đếm `daily_activities` của M12."""

    async def day_counters(self, user_id: int, day: date) -> DayCounters: ...

    async def pages_between(self, user_id: int, start: date, end: date) -> int: ...

    async def study_days(self, user_id: int) -> list[date]: ...


class UserDirectory(Protocol):
    async def profile(self, user_id: int) -> UserProfile: ...


class SeasonRepository(Protocol):
    async def get_containing(self, at: datetime) -> Season | None: ...

    async def ensure(self, starts_at: datetime, ends_at: datetime, now: datetime) -> tuple[Season, bool]:
        """Mùa bắt đầu đúng `starts_at`; chưa có thì tạo với số kỳ = lớn nhất + 1. Hai tiến trình tạo cùng
        lúc chỉ ra một mùa (khóa tư vấn + ràng buộc duy nhất). Trả (mùa, vừa tạo)."""
        ...

    async def missing_week_starts(self, since: datetime, until: datetime) -> list[datetime]:
        """Đầu tuần giờ Việt Nam có sự kiện XP trong [since, until] mà chưa có mùa, từ cũ đến mới."""
        ...

    async def has_unfinished_ended(self, now: datetime) -> bool: ...

    async def claim_ended(self, now: datetime, exclude_ids: Sequence[int]) -> Season | None:
        """Một mùa chưa chốt xong (`active`/`finalizing`) đã quá hạn, khóa dòng (`FOR UPDATE SKIP LOCKED`),
        bỏ qua các mùa trong `exclude_ids`; None nếu không có."""
        ...

    async def set_status(
        self, season_id: int, status: SeasonStatus, finalized_at: datetime | None
    ) -> None: ...

    async def add_results(self, results: Sequence[SeasonResult], now: datetime) -> None:
        """Ghi kết quả; trùng khóa thì bỏ qua (kết quả đã ghi không tính lại)."""
        ...

    async def claim_pending_result(self, season_id: int, skip_users: Sequence[int]) -> SeasonResult | None:
        """Một kết quả chưa trao (`reward_granted_at IS NULL`), khóa dòng bằng `SKIP LOCKED`."""
        ...

    async def mark_granted(self, season_id: int, user_id: int, at: datetime) -> None: ...

    async def count_pending(self, season_id: int) -> int: ...

    async def results_of_user(
        self, user_id: int, offset: int, limit: int
    ) -> tuple[list[SeasonResultRow], int]:
        """Mùa mới nhất trước."""
        ...

    async def result_of_user(self, season_id: int, user_id: int) -> SeasonResult | None: ...


class LeaderboardRepository(Protocol):
    async def page(
        self, metric: LeaderboardMetric, window: LeaderboardWindow, offset: int, limit: int
    ) -> tuple[list[LeaderboardEntry], int]:
        """Trang bảng xếp hạng (tài khoản đang hoạt động, điểm > 0) và tổng số dòng."""
        ...

    async def rank_of(
        self, metric: LeaderboardMetric, window: LeaderboardWindow, user_id: int
    ) -> RankedScore | None: ...

    async def score_at_rank(
        self, metric: LeaderboardMetric, window: LeaderboardWindow, rank: int
    ) -> int | None: ...

    async def top_exp(self, window: LeaderboardWindow, limit: int, min_xp: int) -> list[RankedScore]:
        """Xếp hạng XP của mùa cho việc chốt thưởng (kể cả người ẩn danh), lọc điều kiện XP tối thiểu."""
        ...

    async def totals(
        self, window: LeaderboardWindow, season_window: LeaderboardWindow
    ) -> LeaderboardTotals: ...


class AchievementRepository(Protocol):
    async def list_active(self) -> list[Achievement]: ...

    async def get_by_code(self, code: str) -> Achievement | None:
        """Chỉ huy hiệu đang dùng (`is_active`)."""
        ...

    async def user_rows(self, user_id: int) -> dict[int, UserAchievement]:
        """Huy hiệu đã đạt của người này theo `achievement_id`."""
        ...

    async def upsert_tier(
        self, user_id: int, achievement_id: int, tier: int, source: AchievementSource, now: datetime
    ) -> None:
        """Thêm hoặc nâng cấp (không bao giờ hạ); giữ nguyên nguồn và `unlocked_at` của dòng đã có."""
        ...

    async def equipped_for(self, user_ids: Sequence[int]) -> dict[int, BadgeView]:
        """Huy hiệu đang đeo của nhiều người bằng một truy vấn."""
        ...

    async def set_equipped(self, user_id: int, achievement_id: int | None) -> None:
        """Bỏ đeo cái cũ, đeo cái mới trong cùng giao dịch (tối đa một)."""
        ...


class MetricReader(Protocol):
    """Chỉ số huy hiệu tính khi đánh giá từ dữ liệu của module khác (M03, M06, M07, M08, M12)."""

    async def values(
        self, user_id: int, metrics: Iterable[AchievementMetric], timezone: str
    ) -> dict[AchievementMetric, int]: ...

    async def active_users(self, since: datetime, after_user_id: int, limit: int) -> list[int]:
        """Người có hoạt động học hoặc tra cứu từ `since`, id tăng dần (quét nền, F16.11)."""
        ...


class MinigameRepository(Protocol):
    async def add(self, session: NewMinigameSession) -> MinigameSession: ...

    async def add_round(self, round_: MinigameRound) -> None:
        """Lưu lượt do máy chủ phát (bộ chữ đã phát)."""
        ...

    async def get_round_for_update(self, round_id: uuid.UUID, user_id: int) -> MinigameRound | None:
        """Lượt của đúng người này, khóa dòng tới hết giao dịch; lượt của người khác coi như không có."""
        ...

    async def purge_rounds_before(self, cutoff: datetime, limit: int) -> int:
        """Xóa tối đa `limit` lượt có `issued_at` < cutoff; trả số dòng đã xóa."""
        ...

    async def mark_round_submitted(self, round_id: uuid.UUID, now: datetime) -> bool:
        """Đánh dấu đã nộp nếu chưa nộp; False khi đã có yêu cầu khác nộp trước."""
        ...

    async def best_score(self, user_id: int, hsk_band: int | None) -> int:
        """Điểm cao nhất đã có của người này ở cùng cấp (`None`: chế độ bộ thủ yếu); 0 nếu chưa chơi."""
        ...

    async def best_records(self, user_id: int) -> list[BladeBest]:
        """Kỷ lục theo từng cấp/chế độ của chính người này, một truy vấn GROUP BY."""
        ...


class CharacterSource(Protocol):
    """Dữ liệu chữ Hán cho mini-game (F16.01): bộ thủ yếu và bộ chữ của ván."""

    async def weak_char_counts(self, user_id: int, since: datetime) -> dict[str, int]:
        """Số lượt ôn Quên/Khó gần đây theo từng chữ của từ trong thẻ."""
        ...

    async def hanzi_infos(self, chars: Iterable[str]) -> dict[str, HanziRadicalInfo]:
        """Chỉ chữ có dữ liệu bộ thủ hoặc thành phần."""
        ...

    async def band_chars(self, band: int, limit: int) -> list[CharRow]:
        """Chữ đơn của các từ HSK ở cấp `band` (cấp 7: HSK 7-9), chữ chưa có ở cấp thấp hơn đứng trước,
        thiếu thì bù chữ cấp thấp hơn; mỗi nhóm ngẫu nhiên. Chỉ chữ có pinyin."""
        ...

    async def band_words(self, band: int, limit: int) -> list[WordRow]:
        """Ngẫu nhiên từ hai chữ của đúng cấp `band`."""
        ...

    async def radical_chars(self, user_id: int, radical: str, max_hsk: int, limit: int) -> list[CharRow]:
        """Ngẫu nhiên chữ có bộ thủ `radical`, từ Sổ tay của người này và từ HSK cấp không vượt `max_hsk`."""
        ...

    async def radical_words(self, radical: str, max_hsk: int, limit: int) -> list[WordRow]:
        """Ngẫu nhiên từ hai chữ (cấp HSK không vượt `max_hsk`) có ít nhất một chữ mang bộ thủ `radical`."""
        ...

    async def common_radicals(self, max_hsk: int, limit: int) -> list[WeakRadical]: ...


class RewardGateway(Protocol):
    """Ghi phần thưởng giá trị trao đổi qua M17 (F17.01) trong CÙNG giao dịch với phần còn lại của M16."""

    async def grant(
        self, user_id: int, bundle: RewardBundle, key: str, reason: LedgerReason | None, now: datetime
    ) -> GrantResult: ...

    async def decorations(self, user_ids: Sequence[int], now: datetime) -> Mapping[int, Decoration]:
        """Khung và dấu VIP đang hiệu lực (F17.08), đọc theo lô."""
        ...


class NoticeSender(Protocol):
    async def send(self, notice: Notice) -> None:
        """Gửi thông báo trong ứng dụng; hiện thực tự bắt lỗi và ghi log (không làm hỏng phần thưởng)."""
        ...


class GamificationStore(Protocol):
    """Các kho dữ liệu cùng dùng một phiên (giao dịch)."""

    @property
    def xp(self) -> XpRepository: ...

    @property
    def activity(self) -> ActivityReader: ...

    @property
    def users(self) -> UserDirectory: ...

    @property
    def seasons(self) -> SeasonRepository: ...

    @property
    def leaderboard(self) -> LeaderboardRepository: ...

    @property
    def achievements(self) -> AchievementRepository: ...

    @property
    def metrics(self) -> MetricReader: ...

    @property
    def minigames(self) -> MinigameRepository: ...

    @property
    def chars(self) -> CharacterSource: ...

    @property
    def rewards(self) -> RewardGateway: ...


class GamificationUnitOfWork(GamificationStore, Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    async def __aenter__(self) -> GamificationUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...
