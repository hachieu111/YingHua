"""DTO của M12 Thống kê."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.modules.stats.domain.activity import ActivityDelta
from app.modules.stats.domain.periods import Granularity, PeriodActivity
from app.modules.stats.domain.streak import StreakResult


@dataclass(frozen=True, slots=True)
class LearningFacts:
    """Số liệu học tập hiện tại lấy từ M07/M08 (tính tại thời điểm xem)."""

    words_total: int
    words_known: int
    words_learning: int
    words_ignored: int
    cards_total: int
    cards_due: int
    reviews_total: int
    reviews_today: int
    reviews_recalled: int  # số lượt ôn không chọn "Quên"


@dataclass(frozen=True, slots=True)
class LearningOverview:
    facts: LearningFacts
    retention_rate: float | None  # None: chưa có lượt ôn -> giao diện hiện "Chưa có dữ liệu"
    pages_read_total: int
    study_seconds_total: int
    timezone: str


@dataclass(frozen=True, slots=True)
class ActivityReport:
    granularity: Granularity
    timezone: str
    points: list[PeriodActivity]
    current: PeriodActivity  # 7 ngày gần nhất tính tới hôm nay
    previous: PeriodActivity  # 7 ngày liền trước đó
    delta: ActivityDelta


@dataclass(frozen=True, slots=True)
class StudyDay:
    day: date
    is_study_day: bool
    reviews_count: int
    pages_read: int


@dataclass(frozen=True, slots=True)
class SeriesReadingProgress:
    """Tiến độ đọc một truyện (F12.02, lấy từ M03)."""

    series_id: int
    title: str
    cover_file_id: int | None
    pages_read: int
    pages_total: int
    percent: int
    last_read_at: datetime | None
    resume_chapter_id: int | None
    resume_page_no: int | None
    completed: bool


@dataclass(frozen=True, slots=True)
class StreakReport:
    streak: StreakResult
    week: list[StudyDay]
    reading: list[SeriesReadingProgress]
    timezone: str
    rule: str


@dataclass(frozen=True, slots=True)
class UserCounts:
    total: int
    admins: int
    locked: int
    new_last_7_days: int


@dataclass(frozen=True, slots=True)
class ContentCounts:
    series_total: int
    series_public: int
    chapters: int
    pages: int


@dataclass(frozen=True, slots=True)
class ImagingCounts:
    """Số bản dịch theo trạng thái xử lý ảnh (M04) và thời gian xử lý trung bình."""

    queued: int
    running: int
    done: int
    failed: int
    bubbles: int
    avg_processing_ms: int | None


@dataclass(frozen=True, slots=True)
class VocabCounts:
    entries: int


@dataclass(frozen=True, slots=True)
class ActivityTotals:
    """Tổng hoạt động của mọi người trong một khoảng ngày và số người có học."""

    active_users: int
    reviews_count: int
    pages_read: int
    words_saved: int
    quizzes_done: int
    study_seconds: int


@dataclass(frozen=True, slots=True)
class SystemStats:
    """F12.03 — chỉ số tổng hợp, không chứa nội dung sổ tay hay đáp án của người học."""

    generated_at: datetime
    users: UserCounts
    content: ContentCounts
    imaging: ImagingCounts
    ocr_success_rate: float | None  # done / (done + failed); None khi chưa có trang nào xử lý xong/lỗi
    vocab: VocabCounts
    active_today: ActivityTotals
    active_7_days: ActivityTotals
    active_30_days: ActivityTotals
