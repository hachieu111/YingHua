"""Use case của đợt A1 giai đoạn 6 với bản giả: ghi hoạt động khi chấm thẻ, F08.08, F14.04, F14.05."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from typing import Any

from app.modules.notifications.application.delivery import deliver_notification
from app.modules.notifications.application.dto import NotificationRequest, ReminderConfig
from app.modules.notifications.application.use_cases.send_due_reminders import SendDueRemindersUseCase
from app.modules.notifications.domain.entities import (
    Channel,
    DeliveryStatus,
    NewNotification,
    Notification,
    NotificationKind,
)
from app.modules.notifications.domain.errors import EmailDeliveryError
from app.modules.review.application.dto import GradeCommand
from app.modules.review.application.use_cases.create_cards_for_entry import CreateCardsForEntryUseCase
from app.modules.review.application.use_cases.grade_card import GradeCardUseCase
from app.modules.review.application.use_cases.optimize_fsrs_parameters import (
    OptimizeConfig,
    OptimizeFsrsParametersUseCase,
)
from app.modules.review.domain.entities import Rating
from app.modules.review.domain.fsrs_profile import (
    DEFAULT_DESIRED_RETENTION,
    FsrsOptimizerUnavailableError,
    FsrsProfile,
    InvalidFsrsParametersError,
    OptimizerLog,
)
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
from app.modules.settings.domain.entities import ReminderSetting
from tests.conftest import FixedClock
from tests.unit.activity_fakes import FakeFsrsProfiles
from tests.unit.review_fakes import FakeReviewUow, identity

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)


async def test_grade_card_records_review_and_study_seconds_in_same_transaction() -> None:
    """F12.01: mỗi lượt chấm cộng 1 lượt ôn và thời gian nghĩ; gửi lại cùng mã lượt không cộng lần hai."""
    uow = FakeReviewUow()
    uow.vocab.add_face(1)
    scheduler = FsrsScheduler(enable_fuzzing=False)
    await CreateCardsForEntryUseCase(scheduler).execute(uow.cards, 1, 1, NOW)
    card_id = next(iter(uow.cards.items))
    grade = GradeCardUseCase(lambda: uow, scheduler, FixedClock(NOW))
    command = GradeCommand(card_id, 3, uuid.uuid4(), duration_ms=2600)
    await grade.execute(identity(1), command)
    await grade.execute(identity(1), command)
    assert uow.activity.total("reviews_count") == 1 and uow.activity.total("study_seconds") == 3
    assert uow.activity.records[0][0] == 1


async def test_grade_card_uses_personal_fsrs_profile_when_present() -> None:
    """US-HG-03 TC4: lượt chấm kế tiếp dùng tham số riêng (độ nhớ mong muốn cao hơn → hẹn sớm hơn)."""
    from fsrs.scheduler import DEFAULT_PARAMETERS

    results: dict[float, float] = {}
    for retention in (0.80, 0.97):
        uow = FakeReviewUow()
        uow.vocab.add_face(1)
        scheduler = FsrsScheduler(enable_fuzzing=False)
        await CreateCardsForEntryUseCase(scheduler).execute(uow.cards, 1, 1, NOW)
        card_id = next(iter(uow.cards.items))
        uow.fsrs_profiles.profiles[1] = FsrsProfile(tuple(DEFAULT_PARAMETERS), retention)
        grade = GradeCardUseCase(lambda uow=uow: uow, scheduler, FixedClock(NOW))  # type: ignore[misc]
        # Hai lượt "Được" để thẻ ra khỏi bước học rồi so khoảng ôn.
        first = await grade.execute(identity(1), GradeCommand(card_id, 3, uuid.uuid4()))
        later = FixedClock(first.due_at)
        grade = GradeCardUseCase(lambda uow=uow: uow, scheduler, later)  # type: ignore[misc]
        second = await grade.execute(identity(1), GradeCommand(card_id, 3, uuid.uuid4()))
        results[retention] = second.interval_seconds
    assert results[0.80] > results[0.97]


class _Logs:
    def __init__(self, count: int) -> None:
        self.count = count

    async def list_for_optimizer(self, user_id: int, limit: int) -> list[OptimizerLog]:
        return [OptimizerLog(i % 7, Rating.GOOD, NOW, None) for i in range(self.count)]


class _OptUow:
    def __init__(self, profiles: FakeFsrsProfiles, logs: _Logs) -> None:
        self.fsrs_profiles = profiles
        self.logs = logs

    async def __aenter__(self) -> _OptUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def commit(self) -> None:
        return None


class _Optimizer:
    def __init__(self, outcomes: dict[int, object] | None = None) -> None:
        self.calls = 0
        self.fail: object | None = None

    async def optimize(self, logs: Any) -> tuple[float, ...]:
        self.calls += 1
        if isinstance(self.fail, Exception):
            raise self.fail
        return (1.0,) * 21


def _optimize_case(profiles: FakeFsrsProfiles, optimizer: _Optimizer) -> OptimizeFsrsParametersUseCase:
    return OptimizeFsrsParametersUseCase(
        lambda: _OptUow(profiles, _Logs(400)),  # type: ignore[arg-type,return-value]
        optimizer,
        OptimizeConfig(300, 7, 20),
    )


async def test_optimize_saves_profile_keeping_users_desired_retention() -> None:
    """US-HG-03 TC1: người đủ lượt ôn được lưu tham số mới; độ nhớ mong muốn giữ nguyên."""
    profiles = FakeFsrsProfiles()
    profiles.candidates = [5, 6]
    profiles.profiles[6] = FsrsProfile((0.5,) * 21, 0.85)
    report = await _optimize_case(profiles, _Optimizer()).execute(NOW)
    assert (report.candidates, report.optimized, report.kept, report.failed) == (2, 2, 0, 0)
    assert profiles.profiles[5].desired_retention == DEFAULT_DESIRED_RETENTION
    assert profiles.profiles[6].desired_retention == 0.85 and profiles.profiles[6].weights[0] == 1.0
    assert profiles.review_counts[5] == 400
    assert profiles.last_query is not None and profiles.last_query[0] == 300  # ngưỡng tối thiểu


async def test_optimize_keeps_old_parameters_when_invalid_and_continues_after_error() -> None:
    """US-HG-03 TC3, F08.08: tham số không hợp lệ giữ cũ; lỗi một người không chặn người sau."""
    profiles = FakeFsrsProfiles()
    profiles.candidates = [1, 2]
    old = FsrsProfile((0.5,) * 21, 0.9)
    profiles.profiles[1] = old
    optimizer = _Optimizer()
    optimizer.fail = InvalidFsrsParametersError("bất thường")
    report = await _optimize_case(profiles, optimizer).execute(NOW)
    assert (
        (report.kept, report.optimized) == (2, 0)
        and profiles.profiles[1] == old
        and 2 not in profiles.profiles
    )
    optimizer.fail = RuntimeError("hỏng")
    assert (await _optimize_case(profiles, optimizer).execute(NOW)).failed == 2


async def test_optimize_reports_unavailable_when_optimizer_dependencies_are_missing() -> None:
    profiles = FakeFsrsProfiles()
    profiles.candidates = [1, 2]
    optimizer = _Optimizer()
    optimizer.fail = FsrsOptimizerUnavailableError("thiếu torch")
    report = await _optimize_case(profiles, optimizer).execute(NOW)
    assert report.unavailable and optimizer.calls == 1 and not profiles.profiles


class _Notifs:
    def __init__(self) -> None:
        self.rows: list[Notification] = []

    async def add(self, n: NewNotification) -> Notification:
        row = Notification(
            len(self.rows) + 1,
            n.user_id,
            n.kind,
            n.title,
            n.body,
            n.channel,
            n.status,
            n.created_at,
            n.data,
            sent_at=n.sent_at,
        )
        self.rows.append(row)
        return row

    async def set_delivery(self, notification_id: int, status: str, sent_at: datetime | None) -> None:
        return None


class _Reminders:
    def __init__(self) -> None:
        self.claimed: set[tuple[int, object]] = set()

    async def claim(self, user_id: int, day: object, now: datetime) -> bool:
        if (user_id, day) in self.claimed:
            return False
        self.claimed.add((user_id, day))
        return True


class _User:
    def __init__(self, uid: int, locked: bool = False) -> None:
        self.id, self.email, self.is_locked = uid, f"u{uid}@example.com", locked


class _SettingsSource:
    def __init__(self, items: list[ReminderSetting]) -> None:
        self.items = items

    async def list_enabled(self, after_user_id: int, limit: int) -> list[ReminderSetting]:
        return [i for i in self.items if i.user_id > after_user_id][:limit]


class _Users:
    def __init__(self, users: list[_User]) -> None:
        self.users = {u.id: u for u in users}

    async def get_many(self, ids: Any) -> dict[int, _User]:
        return {i: self.users[i] for i in ids if i in self.users}


class _NotifUow:
    def __init__(
        self, source: _SettingsSource, users: _Users, notifs: _Notifs, reminders: _Reminders
    ) -> None:
        self.reminder_settings, self.users = source, users
        self.notifications, self.reminders = notifs, reminders

    async def __aenter__(self) -> _NotifUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def commit(self) -> None:
        return None


class _Email:
    def __init__(self, fail: bool = False) -> None:
        self.fail, self.sent = fail, []

    async def send(self, to_email: str, subject: str, body: str) -> None:
        if self.fail:
            raise EmailDeliveryError("lỗi")
        self.sent.append(to_email)


class _Due:
    def __init__(self, counts: dict[int, int]) -> None:
        self.counts = counts

    async def count_due(self, user_id: int, now: datetime) -> int:
        return self.counts.get(user_id, 0)


def _reminder_case(email: _Email) -> tuple[SendDueRemindersUseCase, _Notifs, _Reminders]:
    at = time(8, 0)
    settings = [ReminderSetting(i, "Asia/Ho_Chi_Minh", at) for i in (1, 2, 3, 4)]
    notifs, reminders = _Notifs(), _Reminders()
    users = _Users([_User(1), _User(2), _User(3, locked=True)])
    uow = _NotifUow(_SettingsSource(settings), users, notifs, reminders)
    case = SendDueRemindersUseCase(
        lambda: uow,  # type: ignore[arg-type,return-value]
        _Due({1: 5, 2: 0, 3: 9, 4: 3}),
        email,
        ReminderConfig(3),
    )
    return case, notifs, reminders


async def test_reminders_skip_no_cards_locked_and_unknown_users_and_send_once_per_day() -> None:
    """US-HG-04 TC1,2,4: chỉ người có thẻ đến hạn và tài khoản còn hoạt động; mỗi ngày tối đa một lời nhắc."""
    email = _Email()
    case, notifs, _ = _reminder_case(email)
    at = datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)  # 08:30 giờ VN
    report = await case.execute(at)
    assert (report.sent, report.skipped_no_cards, report.skipped_locked) == (1, 1, 2)
    assert email.sent == ["u1@example.com"]
    assert [(n.channel, n.status) for n in notifs.rows] == [
        (Channel.IN_APP, DeliveryStatus.SENT),
        (Channel.EMAIL, DeliveryStatus.SENT),
    ]
    assert "5 thẻ" in notifs.rows[0].title and notifs.rows[0].kind is NotificationKind.REMINDER
    again = await case.execute(at)
    assert again.sent == 0 and again.skipped_already == 1


async def test_email_failure_is_recorded_but_in_app_notification_is_kept_and_not_retried() -> None:
    """US-HG-04 TC3, F14.05: email lỗi vẫn giữ thông báo trong ứng dụng, không gửi lặp trong ngày."""
    case, notifs, _ = _reminder_case(_Email(fail=True))
    at = datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)
    report = await case.execute(at)
    assert report.sent == 1 and report.email_failed == 1
    assert any(n.channel is Channel.IN_APP for n in notifs.rows)
    assert (await case.execute(at)).sent == 0


async def test_deliver_notification_marks_email_failed_without_losing_in_app() -> None:
    uow = _NotifUow(_SettingsSource([]), _Users([]), _Notifs(), _Reminders())
    request = NotificationRequest(1, NotificationKind.REPORT_RESOLVED, "Xong", "nội dung", email_to="a@b.c")
    outcome = await deliver_notification(uow, _Email(fail=True), request, NOW)  # type: ignore[arg-type]
    assert outcome.in_app.status is DeliveryStatus.SENT and outcome.email_failed
    plain = await deliver_notification(
        uow, _Email(), NotificationRequest(1, NotificationKind.REMINDER, "t"), NOW
    )  # type: ignore[arg-type]
    assert plain.email is None
