"""M04 — quy tắc thuần và use case với repository giả: F04.03, F04.05, F04.06, F04.07, F04.13."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.core.errors import PermissionDeniedError
from app.core.stored_files import FileKind, StoredFile
from app.modules.auth.application.public import Identity, Role
from app.modules.imaging.application.dto import JobConfig, JobResult
from app.modules.imaging.application.use_cases.claim_next_job import ClaimNextJobUseCase
from app.modules.imaging.application.use_cases.complete_job import CompleteJobUseCase
from app.modules.imaging.application.use_cases.fail_job import FailJobUseCase
from app.modules.imaging.application.use_cases.list_translations import ListTranslationsUseCase
from app.modules.imaging.application.use_cases.retranslate_page import RetranslatePageUseCase
from app.modules.imaging.application.use_cases.retry_translation import RetryTranslationUseCase
from app.modules.imaging.application.use_cases.save_text_result import SaveTextResultUseCase
from app.modules.imaging.domain.entities import NewBubble, QueueStats, Translation, TranslationStatus
from app.modules.imaging.domain.errors import (
    InvalidBubbleError,
    JobNotRunningError,
    TranslationInProgressError,
    TranslationNotFailedError,
)
from app.modules.imaging.domain.rules import (
    MAX_ERROR_MESSAGE_CHARS,
    ascii_filename,
    clip_error,
    download_filename,
    validate_bubbles,
)
from app.modules.library.application.dto import PageAccess
from tests.conftest import FixedClock

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
STATUS = TranslationStatus


def _translation(tid: int, status: TranslationStatus, attempts: int = 0, **extra: Any) -> Translation:
    return Translation(
        id=tid,
        source_file_id=extra.pop("source_file_id", 100 + tid),
        sha256="a" * 64,
        status=status,
        pipeline_version="v1",
        attempts=attempts,
        queued_at=NOW,
        **extra,
    )


class FakeQueue:
    def __init__(self, *items: Translation) -> None:
        self.items = {t.id: t for t in items}
        self.stale_closed = 0
        self.done_calls: list[tuple[int, int | None, int | None]] = []

    async def get(self, tid: int) -> Translation | None:
        return self.items.get(tid)

    get_for_update = get

    async def requeue_failed(self, tid: int, now: datetime) -> bool:
        t = self.items[tid]
        if t.status is not STATUS.FAILED:
            return False
        t.status, t.attempts, t.error_step, t.error_message = STATUS.QUEUED, 0, None, None
        return True

    async def claim_next(self, worker_id: str, now: datetime, stale_before: datetime) -> Translation | None:
        queued = sorted((t for t in self.items.values() if t.status is STATUS.QUEUED), key=lambda t: t.id)
        if not queued:
            return None
        t = queued[0]
        t.status, t.attempts, t.worker_id = STATUS.RUNNING, t.attempts + 1, worker_id
        return replace(t)

    async def fail_exhausted_stale(self, stale_before: datetime, now: datetime, max_attempts: int) -> int:
        return self.stale_closed

    async def save_partial_stats(self, tid: int, stats: dict[str, Any]) -> None:
        self.items[tid].stats = stats

    async def mark_done(
        self,
        tid: int,
        inpainted: int | None,
        rendered: int | None,
        stats: dict[str, Any],
        ms: int,
        phash: int | None,
        now: datetime,
    ) -> None:
        self.items[tid].status = STATUS.DONE
        self.done_calls.append((tid, inpainted, rendered))

    async def mark_failed(
        self, tid: int, step: str, message: str, requeue: bool, now: datetime
    ) -> TranslationStatus:
        t = self.items[tid]
        t.status = STATUS.QUEUED if requeue else STATUS.FAILED
        t.error_step, t.error_message = step, message
        return t.status

    async def list_page(
        self, status: TranslationStatus | None, offset: int, limit: int
    ) -> tuple[list[Translation], int]:
        rows = [t for t in self.items.values() if status is None or t.status is status]
        return rows[offset : offset + limit], len(rows)

    async def stats(self) -> QueueStats:
        return QueueStats(counts={s.value: 0 for s in STATUS}, avg_processing_ms=None)


class FakeBubbles:
    def __init__(self, existing: int = 0) -> None:
        self.deleted: list[int] = []
        self.added: list[tuple[int, int]] = []
        self.existing = existing
        self.styles: dict[int, Any] = {}

    async def count_by_translation(self, tid: int) -> int:
        return self.existing

    async def update_styles(self, tid: int, styles: dict[int, Any]) -> None:
        self.styles.update(styles)

    async def delete_by_translation(self, tid: int) -> int:
        self.deleted.append(tid)
        return 0

    async def add_many(self, tid: int, bubbles: Any) -> None:
        self.added.append((tid, len(list(bubbles))))


class FakeFiles:
    def __init__(self, *stored: StoredFile) -> None:
        self.items = {f.id: f for f in stored}
        self.deleted: list[int] = []

    async def get(self, file_id: int) -> StoredFile | None:
        return self.items.get(file_id)

    async def delete_many(self, ids: Any) -> list[str]:
        self.deleted.extend(ids)
        return []


class FakeAudit:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    async def add(self, *args: Any) -> None:
        self.calls.append(args)


class FakeUow:
    def __init__(self, queue: FakeQueue, files: FakeFiles | None = None) -> None:
        self.translations = queue
        self.bubbles = FakeBubbles()
        self.files = files or FakeFiles()
        self.audit = FakeAudit()
        self.committed = False

    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


class FakePages:
    def __init__(self, translation_id: int | None, can_edit: bool = True) -> None:
        self._access = PageAccess(
            page_id=1,
            page_no=1,
            translation_id=translation_id,
            original_file_id=1,
            width=100,
            height=200,
            can_edit=can_edit,
        )

    async def get_page(
        self, identity: Identity | None, page_id: int, *, require_edit: bool = False
    ) -> PageAccess:
        if require_edit and not self._access.can_edit:
            raise PermissionDeniedError()
        return self._access


def _identity(role: Role = Role.USER) -> Identity:
    return Identity(user_id=9, role=role, session_id="s")


def _stored(fid: int) -> StoredFile:
    return StoredFile(fid, FileKind.ORIGINAL, f"original/{fid}.png", "b" * 64, "image/png", 10, NOW)


def _bubble(idx: int = 0, class_name: str = "speech_bubble", **extra: Any) -> NewBubble:
    values: dict[str, Any] = {"x": 1, "y": 1, "w": 10, "h": 10, "text_zh": "你好"} | extra
    return NewBubble(idx=idx, class_name=class_name, **values)


def test_clip_error_limits_length_and_drops_traceback() -> None:
    """US-XL-07: lý do lỗi ≤ 1000 ký tự, không stack trace dài."""
    step, message = clip_error("  ocr  ", "x" * 5000)
    assert (step, len(message)) == ("ocr", MAX_ERROR_MESSAGE_CHARS)
    _, short = clip_error("", "line1\nline2\nline3\nline4\nline5\nline6\nline7")
    assert short.splitlines() == ["line1", "line2", "line3", "line4", "line5"]
    assert clip_error("", "")[0] == "unknown"


def test_validate_bubbles_rejects_bad_class_duplicate_idx_and_geometry() -> None:
    validate_bubbles([_bubble(0), _bubble(1, "sound_effect")])
    for bad in (
        [_bubble(0, "unknown_class")],
        [_bubble(0), _bubble(0)],
        [_bubble(0, w=0)],
        [_bubble(0, x=-1)],
        [_bubble(0, text_zh="")],
    ):
        with pytest.raises(InvalidBubbleError):
            validate_bubbles(bad)


def test_download_filename_is_safe_and_ascii_fallback_strips_accents() -> None:
    """US-NH-20: tên tệp theo truyện–chương–trang, không chứa ký tự đường dẫn."""
    name = download_filename("Hoa/Hồng: Đỏ", "1", 3, "rendered", "png")
    assert name == "Hoa-Hồng-Đỏ_ch1_p3_rendered.png"
    assert ascii_filename(name) == "Hoa-Hong-Do_ch1_p3_rendered.png"
    assert download_filename(None, None, 1, "original", "jpg") == "anh-tai-len_p1_original.jpg"


@pytest.mark.parametrize("status", [STATUS.QUEUED, STATUS.RUNNING])
async def test_retranslate_rejects_page_being_processed(status: TranslationStatus) -> None:
    """US-NH-21: không tạo việc trùng cho trang đang chờ/đang xử lý."""
    uow = FakeUow(FakeQueue(_translation(1, status)))
    use_case = RetranslatePageUseCase(lambda: uow, FakePages(1), FixedClock(NOW))  # type: ignore[arg-type,return-value]
    with pytest.raises(TranslationInProgressError):
        await use_case.execute(_identity(), 1)
    assert not uow.committed


async def test_retranslate_rejects_done_page_and_requires_edit_permission() -> None:
    uow = FakeUow(FakeQueue(_translation(1, STATUS.DONE)))
    with pytest.raises(TranslationNotFailedError):
        await RetranslatePageUseCase(lambda: uow, FakePages(1), FixedClock(NOW)).execute(_identity(), 1)  # type: ignore[arg-type,return-value]
    with pytest.raises(PermissionDeniedError):
        await RetranslatePageUseCase(lambda: uow, FakePages(1, can_edit=False), FixedClock(NOW)).execute(  # type: ignore[arg-type,return-value]
            _identity(), 1
        )


async def test_retranslate_requeues_failed_page_and_drops_old_bubbles() -> None:
    queue = FakeQueue(_translation(1, STATUS.FAILED, attempts=2, error_step="ocr", error_message="x"))
    uow = FakeUow(queue)
    result = await RetranslatePageUseCase(lambda: uow, FakePages(1), FixedClock(NOW)).execute(  # type: ignore[arg-type,return-value]
        _identity(), 1
    )
    assert result.status is STATUS.QUEUED and uow.committed
    assert (queue.items[1].attempts, queue.items[1].error_message) == (0, None)
    assert uow.bubbles.deleted == [1]


async def test_retry_translation_is_admin_only_and_audited() -> None:
    """US-QT-07: chỉ quản trị viên chạy lại bản dịch lỗi; ghi nhật ký quản trị."""
    queue = FakeQueue(_translation(1, STATUS.FAILED, attempts=2, error_step="ocr"))
    uow = FakeUow(queue)
    use_case = RetryTranslationUseCase(lambda: uow, FixedClock(NOW))  # type: ignore[arg-type,return-value]
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(_identity(Role.USER), 1)
    await use_case.execute(_identity(Role.ADMIN), 1)
    assert queue.items[1].status is STATUS.QUEUED
    assert [c[1] for c in uow.audit.calls] == ["translation.retry"]
    with pytest.raises(TranslationInProgressError):
        await use_case.execute(_identity(Role.ADMIN), 1)


async def test_list_translations_requires_admin() -> None:
    """US-QT-06: người học không xem được hàng đợi."""
    uow = FakeUow(FakeQueue(_translation(1, STATUS.FAILED)))
    use_case = ListTranslationsUseCase(lambda: uow)  # type: ignore[arg-type,return-value]
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(_identity(), None, 1, 20)
    result = await use_case.execute(_identity(Role.ADMIN), STATUS.FAILED, 1, 20)
    assert result.total == 1


async def test_fail_job_requeues_until_max_attempts_then_fails() -> None:
    """US-XL-07: còn lượt thử → queued; hết lượt → failed."""
    queue = FakeQueue(
        _translation(1, STATUS.RUNNING, attempts=1), _translation(2, STATUS.RUNNING, attempts=2)
    )
    uow = FakeUow(queue)
    use_case = FailJobUseCase(lambda: uow, FixedClock(NOW), JobConfig(max_attempts=2))  # type: ignore[arg-type,return-value]
    assert await use_case.execute(1, "ocr", "boom") is STATUS.QUEUED
    assert await use_case.execute(2, "ocr", "x" * 3000) is STATUS.FAILED
    assert len(queue.items[2].error_message or "") == MAX_ERROR_MESSAGE_CHARS
    with pytest.raises(JobNotRunningError):
        await use_case.execute(1, "ocr", "again")  # đã về queued, không còn running


async def test_complete_job_inserts_bubbles_when_none_exist_and_removes_superseded_files() -> None:
    """US-XL-07: ghi kết quả trong một giao dịch, xóa ảnh dẫn xuất cũ."""
    queue = FakeQueue(_translation(1, STATUS.RUNNING, inpainted_file_id=7, rendered_file_id=8))
    uow = FakeUow(queue)
    use_case = CompleteJobUseCase(lambda: uow, FixedClock(NOW), storage=None)  # type: ignore[arg-type,return-value]
    await use_case.execute(
        1, JobResult(bubbles=[_bubble(0), _bubble(1)], inpainted_file_id=7, rendered_file_id=9)
    )
    assert uow.bubbles.added == [(1, 2)]  # chưa có bong bóng (caller cũ) -> chèn như trước
    assert queue.done_calls == [(1, 7, 9)]
    assert uow.files.deleted == [8]  # chỉ ảnh bị thay mới bị xóa
    with pytest.raises(JobNotRunningError):
        await use_case.execute(1, JobResult(bubbles=[]))  # đã done
    with pytest.raises(InvalidBubbleError):
        await use_case.execute(1, JobResult(bubbles=[_bubble(0, "bad")]))


async def test_complete_job_keeps_existing_bubbles_and_only_updates_style() -> None:
    """F04.02: bong bóng đã ghi ở giai đoạn 1 giữ nguyên (id không đổi), chỉ bổ sung style theo idx."""
    queue = FakeQueue(_translation(1, STATUS.RUNNING))
    uow = FakeUow(queue)
    uow.bubbles.existing = 2
    use_case = CompleteJobUseCase(lambda: uow, FixedClock(NOW), storage=None)  # type: ignore[arg-type,return-value]
    await use_case.execute(
        1,
        JobResult(bubbles=[_bubble(0, style={"c": 1}), _bubble(1)], inpainted_file_id=7, rendered_file_id=9),
    )
    assert uow.bubbles.deleted == [] and uow.bubbles.added == []
    assert uow.bubbles.styles == {0: {"c": 1}} and queue.items[1].status is STATUS.DONE


async def test_save_text_result_replaces_old_bubbles_and_keeps_running() -> None:
    """F04.02: ghi chữ giai đoạn 1 thay bong bóng cũ, vẫn running; việc không running bị từ chối."""
    queue = FakeQueue(_translation(1, STATUS.RUNNING), _translation(2, STATUS.QUEUED))
    uow = FakeUow(queue)
    use_case = SaveTextResultUseCase(lambda: uow)  # type: ignore[arg-type,return-value]
    await use_case.execute(1, [_bubble(0), _bubble(1)], {"mode": "yolo"})
    assert uow.bubbles.deleted == [1] and uow.bubbles.added == [(1, 2)]
    assert (
        queue.items[1].status is STATUS.RUNNING and queue.items[1].stats == {"mode": "yolo"} and uow.committed
    )
    with pytest.raises(JobNotRunningError):
        await use_case.execute(2, [_bubble(0)], {})
    with pytest.raises(InvalidBubbleError):
        await use_case.execute(1, [_bubble(0, "bad")], {})


async def test_claim_next_job_returns_oldest_and_skips_jobs_without_source_file() -> None:
    """US-XL-01: nhận việc cũ nhất; việc mất ảnh gốc bị đóng failed rồi lấy việc kế."""
    queue = FakeQueue(
        _translation(1, STATUS.QUEUED, source_file_id=None),
        _translation(2, STATUS.QUEUED, source_file_id=102),
    )
    uow = FakeUow(queue, FakeFiles(_stored(102)))
    use_case = ClaimNextJobUseCase(lambda: uow, JobConfig(stale_after=timedelta(minutes=15)))  # type: ignore[arg-type,return-value]
    job = await use_case.execute("w1", NOW)
    assert job is not None and (job.translation_id, job.source_storage_key, job.attempts) == (
        2,
        "original/102.png",
        1,
    )
    assert queue.items[1].status is STATUS.FAILED and queue.items[1].error_step == "source"
    assert await use_case.execute("w1", NOW) is None
