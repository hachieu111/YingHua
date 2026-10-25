"""Vòng lặp worker xử lý ảnh với fake (không nạp model, không CSDL).

Liên quan F04.07, F04.13 (hàng đợi, ghi kết quả), F15.03 (tác vụ định kỳ), US-XL-07, US-QT-07 (lỗi đọc được).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.stored_files import FileKind
from app.modules.imaging.application.dto import ClaimedJob, JobResult
from app.modules.imaging.domain.entities import TranslationStatus
from worker.config import LoopTiming, loop_timing_from_settings, pipeline_config_from_settings
from worker.image_codec import phash
from worker.job_processor import UNKNOWN_MESSAGE, CpuRunner, JobProcessor
from worker.loop import WorkerLoop
from worker.main import build_worker
from worker.pipeline_types import BubbleResult, ImageArray, PipelineConfig, PipelineResult, PipelineStepError

T0 = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
SOURCE_KEY = "page/ab/abc.png"
IMG = np.full((40, 60, 3), 200, dtype=np.uint8)


class MutableClock:
    def __init__(self, at: datetime = T0) -> None:
        self.at = at

    def now(self) -> datetime:
        return self.at


def _png(img: ImageArray = IMG) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return bytes(buf.tobytes())


def _job(tid: int = 7) -> ClaimedJob:
    return ClaimedJob(tid, 3, SOURCE_KEY, "image/png", "sha", 1, T0)


class FakeJobs:
    def __init__(self, jobs: list[ClaimedJob] | None = None, store_error: Exception | None = None) -> None:
        self.queue = list(jobs or [])
        self.calls: list[str] = []
        self.stored: list[tuple[bytes, FileKind]] = []
        self.completed: list[tuple[int, JobResult]] = []
        self.failed: list[tuple[int, str, str]] = []
        self._store_error = store_error

    async def claim_next_job(self, worker_id: str, now: datetime) -> ClaimedJob | None:
        self.calls.append("claim")
        return self.queue.pop(0) if self.queue else None

    async def store_result_image(self, data: bytes, kind: FileKind) -> int:
        self.calls.append(f"store:{kind.value}")
        if self._store_error is not None:
            raise self._store_error
        self.stored.append((data, kind))
        return 100 + len(self.stored)

    async def complete_job(self, translation_id: int, result: JobResult) -> None:
        self.calls.append("complete")
        self.completed.append((translation_id, result))

    async def fail_job(self, translation_id: int, error_step: str, error_message: str) -> TranslationStatus:
        self.calls.append("fail")
        self.failed.append((translation_id, error_step, error_message))
        return TranslationStatus.QUEUED


class FakeStorage:
    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.files = files if files is not None else {SOURCE_KEY: _png()}

    async def save(self, data: bytes, folder: str, extension: str) -> str:
        raise AssertionError("worker không ghi trực tiếp vào kho tệp")

    async def read(self, key: str) -> bytes:
        if key not in self.files:
            raise NotFoundError("Tệp không còn tồn tại")
        return self.files[key]

    async def delete(self, key: str) -> None:
        self.files.pop(key, None)


def _bubble(idx: int = 0) -> BubbleResult:
    return BubbleResult(
        idx=idx,
        class_name="speech_bubble",
        x=1,
        y=2,
        w=30,
        h=20,
        polygon=[[1, 2], [31, 2], [31, 22]],
        confidence=0.9,
        text_zh="你好吗",
        pinyin="nǐ hǎo ma",
        text_vi="Bạn khỏe không",
        translate_method="vietphrase",
        lines=[{"text": "你好吗"}],
        tokens=[
            {"w": "你好", "start": 0, "end": 2, "pinyin": "nǐ hǎo"},
            {"w": "吗", "start": 2, "end": 3, "pinyin": "ma"},
        ],
        style={"color": "#000000"},
    )


class FakeAdapter:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls = 0
        self._error = error

    def process(self, image_bgr: ImageArray) -> PipelineResult:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return PipelineResult(
            bubbles=[_bubble()],
            inpainted=np.zeros_like(image_bgr),
            rendered=np.full_like(image_bgr, 255),
            mode="yolo",
            stats={"timings_ms": {"detect": 5, "ocr": 9, "total": 20}, "n_translated": 1},
        )


class FakeEntries:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[list[str]] = []
        self._error = error

    async def find_entry_ids(self, words: Any) -> dict[str, int | None]:
        self.calls.append(list(words))
        if self._error is not None:
            raise self._error
        return {"你好": 11, "吗": None}


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[datetime] = []

    async def run_due_jobs(self, now: datetime, worker_id: str) -> list[Any]:
        self.calls.append(now)
        return []


@pytest.fixture(scope="module")
def cpu() -> Any:
    runner = CpuRunner()
    yield runner
    runner.shutdown()


def _processor(
    cpu: CpuRunner,
    jobs: FakeJobs,
    adapter: FakeAdapter | None = None,
    storage: FakeStorage | None = None,
    entries: FakeEntries | None = None,
) -> JobProcessor:
    return JobProcessor(
        jobs,
        storage or FakeStorage(),
        adapter or FakeAdapter(),
        entries or FakeEntries(),
        MutableClock(),
        cpu,
    )


async def test_successful_job_stores_images_before_completing_and_maps_bubbles(cpu: CpuRunner) -> None:
    """US-XL-07: ảnh kết quả lưu trước, rồi mới ghi bong bóng + đóng việc."""
    jobs, entries = FakeJobs([_job(7)]), FakeEntries()
    outcome = await _processor(cpu, jobs, entries=entries).process_next("w1")

    assert outcome is not None and outcome.ok
    assert jobs.calls == ["claim", "store:inpainted", "store:rendered", "complete"]
    assert entries.calls == [["你好", "吗"]]
    tid, result = jobs.completed[0]
    assert tid == 7
    assert (result.inpainted_file_id, result.rendered_file_id) == (101, 102)
    assert all(data.startswith(b"\xff\xd8\xff") for data, _ in jobs.stored)  # JPEG
    bubble = result.bubbles[0]
    assert (bubble.idx, bubble.class_name, bubble.x, bubble.y, bubble.w, bubble.h) == (
        0,
        "speech_bubble",
        1,
        2,
        30,
        20,
    )
    assert bubble.text_zh == "你好吗" and bubble.text_vi == "Bạn khỏe không"
    assert bubble.translate_method == "vietphrase" and bubble.style == {"color": "#000000"}
    assert list(bubble.tokens) == [
        {"word": "你好", "pinyin": "nǐ hǎo", "entry_id": 11},
        {"word": "吗", "pinyin": "ma", "entry_id": None},
    ]
    assert result.stats["timings_ms"] == {"detect": 5, "ocr": 9, "total": 20}
    assert result.stats["mode"] == "yolo"
    assert result.processing_ms >= 0
    assert result.phash == phash(IMG)


async def test_pipeline_step_error_fails_job_with_that_step(cpu: CpuRunner) -> None:
    """US-QT-07: lỗi ở bước OCR → việc ghi đúng bước và thông điệp đọc được."""
    jobs = FakeJobs([_job(8)])
    adapter = FakeAdapter(PipelineStepError("ocr", "Lỗi khi nhận dạng chữ (OCR) (RuntimeError)"))
    outcome = await _processor(cpu, jobs, adapter).process_next("w1")

    assert outcome is not None and not outcome.ok and outcome.error_step == "ocr"
    assert outcome.status is TranslationStatus.QUEUED
    assert jobs.failed == [(8, "ocr", "Lỗi khi nhận dạng chữ (OCR) (RuntimeError)")]
    assert "complete" not in jobs.calls and not jobs.stored


async def test_unexpected_error_fails_job_as_unknown_without_details(cpu: CpuRunner) -> None:
    jobs = FakeJobs([_job(9)])
    adapter = FakeAdapter(ZeroDivisionError("chi tiết nội bộ C:\\server\\x.py"))
    await _processor(cpu, jobs, adapter).process_next("w1")

    assert jobs.failed == [(9, "unknown", UNKNOWN_MESSAGE)]


async def test_missing_or_corrupt_source_fails_at_load_without_running_pipeline(cpu: CpuRunner) -> None:
    adapter = FakeAdapter()
    missing = FakeJobs([_job(10)])
    await _processor(cpu, missing, adapter, storage=FakeStorage({})).process_next("w1")
    corrupt = FakeJobs([_job(11)])
    await _processor(
        cpu, corrupt, adapter, storage=FakeStorage({SOURCE_KEY: b"khong-phai-anh"})
    ).process_next("w1")

    assert adapter.calls == 0
    assert [f[:2] for f in missing.failed + corrupt.failed] == [(10, "load"), (11, "load")]


async def test_store_error_fails_job_at_store_step(cpu: CpuRunner) -> None:
    jobs = FakeJobs([_job(12)], store_error=OSError("đĩa đầy"))
    await _processor(cpu, jobs).process_next("w1")

    assert jobs.failed == [(12, "store", "Không lưu được ảnh kết quả")]
    assert "complete" not in jobs.calls


async def test_dictionary_error_keeps_job_with_empty_entry_ids(cpu: CpuRunner) -> None:
    jobs = FakeJobs([_job(13)])
    await _processor(cpu, jobs, entries=FakeEntries(RuntimeError("db"))).process_next("w1")

    tokens = list(jobs.completed[0][1].bubbles[0].tokens)
    assert [t["entry_id"] for t in tokens] == [None, None]


async def test_empty_queue_does_not_call_adapter(cpu: CpuRunner) -> None:
    jobs, adapter = FakeJobs([]), FakeAdapter()
    assert await _processor(cpu, jobs, adapter).process_next("w1") is None
    assert adapter.calls == 0 and jobs.calls == ["claim"]


def _settings(tmp_path: Path, enabled: bool, **extra: Any) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://u:p@127.0.0.1:1/khong_dung_test",
        jwt_secret="x" * 32,  # type: ignore[arg-type]
        pipeline_enabled=enabled,
        storage_dir=tmp_path,
        **extra,
    )


async def test_pipeline_disabled_does_not_create_adapter(tmp_path: Path) -> None:
    created: list[PipelineConfig] = []

    def factory(config: PipelineConfig) -> FakeAdapter:
        created.append(config)
        return FakeAdapter()

    app = build_worker(_settings(tmp_path, False), MutableClock(), factory, "w-test")
    await app.aclose()

    assert created == [] and app.cpu is None


async def test_pipeline_enabled_creates_one_adapter_with_env_paths(tmp_path: Path) -> None:
    created: list[PipelineConfig] = []

    def factory(config: PipelineConfig) -> FakeAdapter:
        created.append(config)
        return FakeAdapter()

    settings = _settings(tmp_path, True, yolo_model_path=tmp_path / "m.pt")
    app = build_worker(settings, MutableClock(), factory, "w-test")
    await app.aclose()

    assert len(created) == 1
    assert created[0].yolo_model_path == tmp_path / "m.pt"
    assert created[0].pipeline_dir.name == "mudule xu ly anh"


async def test_scheduler_runs_on_its_own_interval() -> None:
    clock, runner = MutableClock(), FakeRunner()
    loop = WorkerLoop("w1", runner, None, clock, LoopTiming(0.01, 30, 60))

    for offset in (0, 10, 29, 30, 45, 61):
        clock.at = T0 + timedelta(seconds=offset)
        await loop.run_once()

    assert runner.calls == [T0, T0 + timedelta(seconds=30), T0 + timedelta(seconds=61)]


async def test_loop_counts_outcomes_and_stops_when_requested(cpu: CpuRunner) -> None:
    jobs = FakeJobs([_job(1), _job(2)])
    adapter = FakeAdapter()
    loop = WorkerLoop("w1", FakeRunner(), _processor(cpu, jobs, adapter), MutableClock(), LoopTiming(0.01))

    assert await loop.run_once() is True
    assert await loop.run_once() is True
    assert await loop.run_once() is False
    assert (loop.counters.done, loop.counters.failed) == (2, 0)

    loop.request_stop()
    await loop.run()  # thoát ngay, không nhận việc mới
    assert jobs.calls.count("claim") == 3


def test_settings_overrides_and_defaults(tmp_path: Path) -> None:
    assert loop_timing_from_settings(_settings(tmp_path, False)).poll_seconds == 3.0
    assert loop_timing_from_settings(_settings(tmp_path, False, worker_poll_seconds=0.5)).poll_seconds == 0.5
    with pytest.raises(ValueError):
        _settings(tmp_path, False, worker_poll_seconds=0)
    config = pipeline_config_from_settings(_settings(tmp_path, False))
    assert config.font_dir.name == "Font chữ truyện tranh Comic"
    assert config.xianxia_dict_dir.name == "từ điển tu tiên"
    relative = pipeline_config_from_settings(_settings(tmp_path, False, font_dir="fonts"))
    assert relative.font_dir.is_absolute() and relative.font_dir.name == "fonts"


def test_phash_is_signed_64_bit() -> None:
    rng = np.random.default_rng(0)
    for _ in range(5):
        value = phash(rng.integers(0, 256, (50, 70, 3), dtype=np.uint8))
        assert -(1 << 63) <= value < (1 << 63)
