from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.stats.application.dto import (
    ActivityReport,
    ActivityTotals,
    LearningOverview,
    SeriesReadingProgress,
    StreakReport,
    StudyDay,
    SystemStats,
)
from app.modules.stats.application.use_cases.get_today_plan import TodayPlan
from app.modules.stats.domain.activity import ActivityDelta
from app.modules.stats.domain.periods import PeriodActivity

READING_HINT = "Bạn chưa đọc truyện nào. Hãy mở một truyện và đọc trang đầu tiên để bắt đầu."


class LearningOverviewResponse(BaseModel):
    words_total: int = Field(description="Số mục từ trong sổ tay")
    words_known: int
    words_learning: int
    words_ignored: int
    cards_total: int
    cards_due: int = Field(description="Thẻ đến hạn tại thời điểm xem (cùng điều kiện F08.01)")
    reviews_total: int
    reviews_today: int
    retention_rate: float | None = Field(
        description='Tỉ lệ lượt ôn không chọn Quên, 0..1; null khi chưa có lượt ôn (hiện "Chưa có dữ liệu")'
    )
    pages_read_total: int
    study_seconds_total: int
    timezone: str

    @classmethod
    def from_overview(cls, o: LearningOverview) -> LearningOverviewResponse:
        f = o.facts
        return cls(
            words_total=f.words_total,
            words_known=f.words_known,
            words_learning=f.words_learning,
            words_ignored=f.words_ignored,
            cards_total=f.cards_total,
            cards_due=f.cards_due,
            reviews_total=f.reviews_total,
            reviews_today=f.reviews_today,
            retention_rate=o.retention_rate,
            pages_read_total=o.pages_read_total,
            study_seconds_total=o.study_seconds_total,
            timezone=o.timezone,
        )


class ActivityPointResponse(BaseModel):
    start: date
    end: date
    words_saved: int
    reviews_count: int
    pages_read: int
    quizzes_done: int
    study_seconds: int

    @classmethod
    def from_period(cls, p: PeriodActivity) -> ActivityPointResponse:
        return cls(
            start=p.start,
            end=p.end,
            words_saved=p.words_saved,
            reviews_count=p.reviews_count,
            pages_read=p.pages_read,
            quizzes_done=p.quizzes_done,
            study_seconds=p.study_seconds,
        )


class ActivityDeltaResponse(BaseModel):
    words_saved: int
    reviews_count: int
    pages_read: int
    quizzes_done: int
    study_seconds: int

    @classmethod
    def from_delta(cls, d: ActivityDelta) -> ActivityDeltaResponse:
        return cls(
            words_saved=d.words_saved,
            reviews_count=d.reviews_count,
            pages_read=d.pages_read,
            quizzes_done=d.quizzes_done,
            study_seconds=d.study_seconds,
        )


class ActivityResponse(BaseModel):
    granularity: Literal["day", "week", "month"]
    timezone: str
    points: list[ActivityPointResponse]
    current_week: ActivityPointResponse = Field(description="7 ngày gần nhất tính tới hôm nay")
    previous_week: ActivityPointResponse = Field(description="7 ngày liền trước đó")
    delta: ActivityDeltaResponse = Field(description="current_week trừ previous_week; có thể âm")

    @classmethod
    def from_report(cls, r: ActivityReport) -> ActivityResponse:
        return cls(
            granularity=r.granularity.value,
            timezone=r.timezone,
            points=[ActivityPointResponse.from_period(p) for p in r.points],
            current_week=ActivityPointResponse.from_period(r.current),
            previous_week=ActivityPointResponse.from_period(r.previous),
            delta=ActivityDeltaResponse.from_delta(r.delta),
        )


class StudyDayResponse(BaseModel):
    date: date
    studied: bool
    reviews_count: int
    pages_read: int

    @classmethod
    def from_day(cls, d: StudyDay) -> StudyDayResponse:
        return cls(date=d.day, studied=d.is_study_day, reviews_count=d.reviews_count, pages_read=d.pages_read)


class SeriesProgressResponse(BaseModel):
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

    @classmethod
    def from_progress(cls, p: SeriesReadingProgress) -> SeriesProgressResponse:
        return cls(
            series_id=p.series_id,
            title=p.title,
            cover_file_id=p.cover_file_id,
            pages_read=p.pages_read,
            pages_total=p.pages_total,
            percent=p.percent,
            last_read_at=p.last_read_at,
            resume_chapter_id=p.resume_chapter_id,
            resume_page_no=p.resume_page_no,
            completed=p.completed,
        )


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    studied_today: bool
    week: list[StudyDayResponse] = Field(description="7 ngày gần nhất, cũ nhất trước, cuối cùng là hôm nay")
    reading: list[SeriesProgressResponse]
    reading_hint: str | None = Field(description="Gợi ý bắt đầu khi chưa đọc truyện nào")
    rule: str = Field(description="Quy tắc chuỗi ngày học, hiển thị trên giao diện")
    timezone: str

    @classmethod
    def from_report(cls, r: StreakReport) -> StreakResponse:
        return cls(
            current_streak=r.streak.current,
            longest_streak=r.streak.longest,
            studied_today=r.streak.active_today,
            week=[StudyDayResponse.from_day(d) for d in r.week],
            reading=[SeriesProgressResponse.from_progress(p) for p in r.reading],
            reading_hint=None if r.reading else READING_HINT,
            rule=r.rule,
            timezone=r.timezone,
        )


class ActivityTotalsResponse(BaseModel):
    active_users: int
    reviews_count: int
    pages_read: int
    words_saved: int
    quizzes_done: int
    study_seconds: int

    @classmethod
    def from_totals(cls, t: ActivityTotals) -> ActivityTotalsResponse:
        return cls(
            active_users=t.active_users,
            reviews_count=t.reviews_count,
            pages_read=t.pages_read,
            words_saved=t.words_saved,
            quizzes_done=t.quizzes_done,
            study_seconds=t.study_seconds,
        )


class UsersStatsResponse(BaseModel):
    total: int
    admins: int
    locked: int
    new_last_7_days: int


class ContentStatsResponse(BaseModel):
    series_total: int
    series_public: int
    chapters: int
    pages: int


class ImagingStatsResponse(BaseModel):
    pages_queued: int
    pages_running: int
    pages_done: int
    pages_failed: int
    bubbles: int
    avg_processing_ms: int | None
    ocr_success_rate: float | None = Field(
        description="done / (done + failed), 0..1; null khi chưa có dữ liệu"
    )
    ocr_failure_rate: float | None


class SystemStatsResponse(BaseModel):
    generated_at: datetime
    users: UsersStatsResponse
    content: ContentStatsResponse
    imaging: ImagingStatsResponse
    words_saved_total: int
    activity_today: ActivityTotalsResponse
    activity_7_days: ActivityTotalsResponse
    activity_30_days: ActivityTotalsResponse

    @classmethod
    def from_stats(cls, s: SystemStats) -> SystemStatsResponse:
        rate = s.ocr_success_rate
        return cls(
            generated_at=s.generated_at,
            users=UsersStatsResponse(
                total=s.users.total,
                admins=s.users.admins,
                locked=s.users.locked,
                new_last_7_days=s.users.new_last_7_days,
            ),
            content=ContentStatsResponse(
                series_total=s.content.series_total,
                series_public=s.content.series_public,
                chapters=s.content.chapters,
                pages=s.content.pages,
            ),
            imaging=ImagingStatsResponse(
                pages_queued=s.imaging.queued,
                pages_running=s.imaging.running,
                pages_done=s.imaging.done,
                pages_failed=s.imaging.failed,
                bubbles=s.imaging.bubbles,
                avg_processing_ms=s.imaging.avg_processing_ms,
                ocr_success_rate=rate,
                ocr_failure_rate=None if rate is None else 1 - rate,
            ),
            words_saved_total=s.vocab.entries,
            activity_today=ActivityTotalsResponse.from_totals(s.active_today),
            activity_7_days=ActivityTotalsResponse.from_totals(s.active_7_days),
            activity_30_days=ActivityTotalsResponse.from_totals(s.active_30_days),
        )


class TodayActionResponse(BaseModel):
    type: str = Field(description="review | reader | quiz | library | chapter_suggestions")
    deck: str | None = None
    series_id: int | None = None
    chapter_id: int | None = None
    page_no: int | None = None


class TodayItemResponse(BaseModel):
    kind: str = Field(
        description=(
            "review_due | continue_reading | take_quiz | weekly_goal | chapter_suggestions | get_started"
        )
    )
    title: str
    message: str = Field(description="Câu nhắc tiếng Việt sinh theo mẫu, đã điền số liệu")
    count: int | None = Field(
        description="Số liệu chính của việc (thẻ, từ, trang còn thiếu); null nếu không có"
    )
    urgent: bool = Field(description="Nổi bật/ưu tiên (thẻ đến hạn từ ngưỡng cấu hình)")
    priority: int = Field(description="Thứ tự hiển thị, 1 = đầu danh sách")
    action: TodayActionResponse


class TodayResponse(BaseModel):
    items: list[TodayItemResponse]
    all_done: bool = Field(description="Không còn việc nào: giao diện hiện lời chúc kèm lối đi tới Thư viện")
    message: str | None
    timezone: str

    @classmethod
    def from_plan(cls, plan: TodayPlan) -> TodayResponse:
        return cls(
            items=[
                TodayItemResponse(
                    kind=i.kind.value,
                    title=i.title,
                    message=i.message,
                    count=i.count,
                    urgent=i.urgent,
                    priority=i.priority,
                    action=TodayActionResponse(
                        type=i.action.type,
                        deck=i.action.deck,
                        series_id=i.action.series_id,
                        chapter_id=i.action.chapter_id,
                        page_no=i.action.page_no,
                    ),
                )
                for i in plan.items
            ],
            all_done=plan.all_done,
            message=plan.message,
            timezone=plan.timezone,
        )
