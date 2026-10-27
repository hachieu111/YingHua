"""Quy tắc thuần của đợt A1 giai đoạn 6: chuỗi ngày học, kỳ thống kê, báo lỗi, giờ nhắc, xuất sổ tay, FSRS."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest
from fsrs.scheduler import DEFAULT_PARAMETERS

from app.core.errors import InvalidInputError
from app.modules.notifications.domain.entities import ReportStatus, ReportType
from app.modules.notifications.domain.errors import (
    InvalidReportStatusError,
    ReportContentRequiredError,
    ReportTextTooLongError,
)
from app.modules.notifications.domain.rules import (
    normalize_report,
    parse_resolution,
    reminder_day_if_due,
    reminder_message,
)
from app.modules.review.domain.fsrs_profile import InvalidFsrsParametersError
from app.modules.review.infrastructure.fsrs_optimizer import ensure_sane
from app.modules.stats.domain.activity import (
    MAX_STUDY_SECONDS_PER_REVIEW,
    DayActivity,
    local_date,
    study_seconds_from_ms,
)
from app.modules.stats.domain.periods import (
    Granularity,
    check_count,
    parse_granularity,
    period_ranges,
    sum_period,
)
from app.modules.stats.domain.streak import compute_streak
from app.modules.vocab.domain.entities import VocabEntry, VocabOrigin, VocabStatus
from app.modules.vocab.domain.export import (
    EmptyExportError,
    ExportFormat,
    InvalidExportFormatError,
    export_filename,
    parse_export_format,
    render_anki,
    render_csv,
    render_export,
)

TODAY = date(2026, 10, 25)


def _days(*offsets: int) -> list[date]:
    return [TODAY - timedelta(days=n) for n in offsets]


def test_streak_counts_consecutive_days_ending_today() -> None:
    """US-NH-57 TC1: học hôm nay thì chuỗi tính cả hôm nay."""
    result = compute_streak(_days(0, 1, 2, 5, 6), TODAY)
    assert (result.current, result.longest, result.active_today) == (3, 3, True)


def test_streak_keeps_until_end_of_today_when_today_not_studied_yet() -> None:
    result = compute_streak(_days(1, 2), TODAY)
    assert (result.current, result.active_today) == (2, False)


def test_streak_resets_to_zero_after_a_missed_day() -> None:
    """US-NH-57 TC2: bỏ lỡ trọn một ngày thì chuỗi về 0, chuỗi dài nhất vẫn giữ."""
    result = compute_streak(_days(2, 3, 4, 5), TODAY)
    assert (result.current, result.longest) == (0, 4)


def test_streak_of_new_user_is_zero_and_ignores_future_days() -> None:
    assert compute_streak([], TODAY).current == 0
    assert compute_streak([TODAY + timedelta(days=3)], TODAY).longest == 0


def test_local_date_follows_learner_timezone_and_falls_back_to_utc() -> None:
    late_utc = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)
    assert local_date(late_utc, "Asia/Ho_Chi_Minh") == date(2026, 10, 26)
    assert local_date(late_utc, "Khong/Ton_Tai") == date(2026, 10, 25)


def test_study_seconds_rounds_and_caps_each_review() -> None:
    assert study_seconds_from_ms(None) == 0 and study_seconds_from_ms(0) == 0
    assert study_seconds_from_ms(1499) == 1 and study_seconds_from_ms(1500) == 2
    assert study_seconds_from_ms(10**9) == MAX_STUDY_SECONDS_PER_REVIEW


def test_period_ranges_day_week_month() -> None:
    days = period_ranges(Granularity.DAY, TODAY, 3)
    assert days[-1] == (TODAY, TODAY) and len(days) == 3
    weeks = period_ranges(Granularity.WEEK, TODAY, 2)  # 25/10/2026 là Chủ nhật
    assert weeks[-1] == (date(2026, 10, 19), date(2026, 10, 25)) and weeks[0][0] == date(2026, 10, 12)
    months = period_ranges(Granularity.MONTH, date(2026, 1, 15), 2)
    assert months == [(date(2025, 12, 1), date(2025, 12, 31)), (date(2026, 1, 1), date(2026, 1, 31))]


def test_sum_period_adds_only_days_in_range() -> None:
    rows = [DayActivity(TODAY, reviews_count=2, pages_read=1), DayActivity(TODAY - timedelta(days=9), 5)]
    total = sum_period(rows, TODAY - timedelta(days=6), TODAY)
    assert (total.reviews_count, total.pages_read) == (2, 1)


def test_granularity_and_count_validation() -> None:
    assert parse_granularity("week") is Granularity.WEEK
    with pytest.raises(InvalidInputError):
        parse_granularity("year")
    with pytest.raises(InvalidInputError):
        check_count(Granularity.MONTH, 25)


def test_report_needs_a_type_or_a_description() -> None:
    """US-NH-58 TC2."""
    with pytest.raises(ReportContentRequiredError):
        normalize_report(None, "   ")
    with pytest.raises(ReportContentRequiredError):
        normalize_report("other", "")
    assert normalize_report("ocr", "") == (ReportType.OCR, "")
    assert normalize_report(None, " dịch sai ") == (ReportType.OTHER, "dịch sai")
    with pytest.raises(ReportTextTooLongError):
        normalize_report("ocr", "x" * 1001)


def test_resolution_only_allows_resolved_or_rejected() -> None:
    assert parse_resolution("resolved", "  ok ") == (ReportStatus.RESOLVED, "ok")
    assert parse_resolution("rejected", None) == (ReportStatus.REJECTED, None)
    for bad in ("new", "closed"):
        with pytest.raises(InvalidReportStatusError):
            parse_resolution(bad, None)


def test_reminder_is_due_only_inside_grace_window_of_the_learner_local_day() -> None:
    """US-HG-04 TC1: theo múi giờ của người học, trong khung [giờ nhắc, giờ nhắc + 3 giờ]."""
    grace = timedelta(hours=3)
    at = time(8, 30)
    vn = "Asia/Ho_Chi_Minh"
    assert reminder_day_if_due(datetime(2026, 10, 25, 1, 29, tzinfo=timezone.utc), vn, at, grace) is None
    assert reminder_day_if_due(datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc), vn, at, grace) == date(
        2026, 10, 25
    )
    assert reminder_day_if_due(datetime(2026, 10, 25, 4, 31, tzinfo=timezone.utc), vn, at, grace) is None
    late = reminder_day_if_due(datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc), vn, time(23, 0), grace)
    assert late is None  # 03:00 giờ VN hôm sau, chưa tới 23:00 của ngày mới
    title, body = reminder_message(7)
    assert "7" in title and "7" in body


def _entry(term: str, **kw: object) -> VocabEntry:
    now = datetime(2026, 10, 25, tzinfo=timezone.utc)
    base: dict[str, object] = {
        "id": 1,
        "user_id": 1,
        "term": term,
        "status": VocabStatus.LEARNING,
        "origin": VocabOrigin.MANUAL,
        "hsk_source": "none",
        "created_at": now,
        "updated_at": now,
    }
    return VocabEntry(**{**base, **kw})  # type: ignore[arg-type]


def test_csv_has_bom_header_and_neutralises_formulas() -> None:
    """US-NH-60 TC1,5."""
    data = render_csv(
        [
            _entry(
                "学习",
                pinyin="xué xí",
                meaning_vi="học",
                hsk_level=1,
                note='=SUM(1,2) "x"',
                status=VocabStatus.KNOWN,
            )
        ]
    )
    assert data.startswith(b"\xef\xbb\xbf")
    lines = data.decode("utf-8-sig").split("\r\n")
    assert lines[0] == "Chữ Hán,Pinyin,Nghĩa,Cấp HSK,Trạng thái,Ghi chú"
    assert lines[1].startswith("学习,xué xí,học,HSK 1,Đã thuộc,") and "'=SUM(1,2)" in lines[1]


def test_anki_file_has_directives_and_three_tab_columns() -> None:
    """US-NH-60 TC2: mặt trước chữ Hán, mặt sau nghĩa."""
    text = render_anki([_entry("你好", pinyin="nǐ hǎo", meaning_vi="xin\tchào\nbạn", hsk_level=2)]).decode()
    lines = text.splitlines()
    assert lines[:3] == ["#separator:tab", "#html:false", "#tags column:3"]
    assert lines[3].split("\t") == ["你好", "nǐ hǎo — xin chào bạn", "YingHua HSK2 dang_hoc"]


def test_export_rejects_empty_and_unknown_format_and_names_file_safely() -> None:
    """US-NH-60 TC3."""
    with pytest.raises(EmptyExportError):
        render_export(ExportFormat.CSV, [], TODAY)
    with pytest.raises(InvalidExportFormatError):
        parse_export_format("pdf")
    assert export_filename(ExportFormat.CSV, TODAY) == "yinghua-sotay-20261025.csv"
    assert export_filename(ExportFormat.ANKI, TODAY).endswith("-anki.txt")


def test_default_fsrs_weights_are_sane_and_broken_ones_are_rejected() -> None:
    """US-HG-03 TC3: tham số ngoài miền hoặc làm lịch bất thường thì bị từ chối."""
    ensure_sane(DEFAULT_PARAMETERS)
    out_of_range = list(DEFAULT_PARAMETERS)
    out_of_range[0] = 10_000.0
    with pytest.raises(InvalidFsrsParametersError):
        ensure_sane(out_of_range)
    with pytest.raises(InvalidFsrsParametersError):
        ensure_sane(list(DEFAULT_PARAMETERS)[:5])
