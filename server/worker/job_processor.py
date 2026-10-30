"""Xử lý một việc của hàng đợi `translations`: đọc ảnh → giai đoạn chữ → giai đoạn ảnh (F04.02).

Giai đoạn 1 (detect, OCR, dịch, tách từ) xong thì `save_text_result` ghi bong bóng ngay để người học đọc
trong khi giai đoạn 2 (xóa chữ, đắp chữ) còn chạy. Giai đoạn 2 chỉ cập nhật `style` của bong bóng đã có
(id không đổi) cùng ảnh và đặt `done`; lỗi giai đoạn 2 giữ nguyên bong bóng.
Thứ tự bắt buộc của M04: `store_result_image` (ảnh xóa chữ, ảnh đã dịch) **trước** `complete_job`.
Lỗi: `PipelineStepError` → `fail_job` đúng bước; lỗi đọc/lưu tệp → bước `load`/`store`;
lỗi khác → bước `unknown` với thông điệp chung (chi tiết chỉ nằm trong log, không ghi stack trace vào CSDL).
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime
from time import perf_counter
from typing import Any, Protocol, TypeVar

from app.core.clock import Clock
from app.core.errors import NotFoundError
from app.core.logging import request_id_var
from app.core.storage import FileStorage
from app.core.stored_files import FileKind
from app.modules.imaging.application.dto import ClaimedJob, JobResult
from app.modules.imaging.domain.entities import NewBubble, TranslationStatus
from worker.entry_lookup import EntryIdLookup
from worker.image_codec import decode_image, encode_jpeg, phash
from worker.pipeline_types import (
    BubbleResult,
    ImageArray,
    ImagePhaseResult,
    PipelineStepError,
    TextPhaseResult,
)

log = logging.getLogger("yinghua.worker")

T = TypeVar("T")

UNKNOWN_STEP = "unknown"
UNKNOWN_MESSAGE = "Lỗi không xác định khi xử lý ảnh"
LOAD_STEP = "load"
STORE_STEP = "store"


class JobQueue(Protocol):
    """Phần của `WorkerJobs` (M04) mà worker dùng."""

    async def claim_next_job(self, worker_id: str, now: datetime) -> ClaimedJob | None: ...

    async def store_result_image(self, data: bytes, kind: FileKind) -> int: ...

    async def save_text_result(
        self, translation_id: int, bubbles: Sequence[NewBubble], partial_stats: dict[str, Any]
    ) -> None: ...

    async def complete_job(self, translation_id: int, result: JobResult) -> None: ...

    async def fail_job(
        self, translation_id: int, error_step: str, error_message: str
    ) -> TranslationStatus: ...


class PageProcessor(Protocol):
    """`PipelineAdapter` hoặc bản giả trong test."""

    def process_text(self, image_bgr: ImageArray) -> TextPhaseResult: ...

    def process_images(self, text: TextPhaseResult) -> ImagePhaseResult: ...


class CpuRunner:
    """Chạy việc nặng CPU trên **một** luồng riêng, không chặn event loop (model AI không chạy song song)."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pipeline")

    async def run(self, func: Callable[[], T]) -> T:
        # Sao chép context để log trong luồng pipeline vẫn mang mã job (request_id).
        ctx = contextvars.copy_context()
        return await asyncio.get_running_loop().run_in_executor(self._executor, ctx.run, func)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)


@dataclass(frozen=True, slots=True)
class JobOutcome:
    translation_id: int
    ok: bool
    error_step: str | None = None
    # Trạng thái sau `fail_job` (queued/failed); None nếu không ghi được lỗi.
    status: TranslationStatus | None = None


@dataclass(frozen=True, slots=True)
class _Encoded:
    inpainted: bytes
    rendered: bytes
    phash: int


class _JobStepError(Exception):
    """Lỗi ở phần việc của worker (đọc ảnh gốc, lưu ảnh kết quả); `message` an toàn để hiện cho người dùng."""

    def __init__(self, step: str, message: str) -> None:
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.message = message


def _encode_all(source: ImageArray, result: ImagePhaseResult) -> _Encoded:
    return _Encoded(encode_jpeg(result.inpainted), encode_jpeg(result.rendered), phash(source))


def to_new_bubble(b: BubbleResult, entry_ids: dict[str, int | None]) -> NewBubble:
    """Ánh xạ kết quả adapter sang `NewBubble`; token `{w, pinyin}` → `{word, pinyin, entry_id}`."""
    tokens = [
        {"word": t["w"], "pinyin": t.get("pinyin") or None, "entry_id": entry_ids.get(t["w"])}
        for t in b.tokens
        if t.get("w")
    ]
    return NewBubble(
        idx=b.idx,
        class_name=b.class_name,
        x=b.x,
        y=b.y,
        w=b.w,
        h=b.h,
        text_zh=b.text_zh,
        polygon=b.polygon,
        confidence=b.confidence,
        pinyin=b.pinyin or None,
        text_vi=b.text_vi or None,
        translate_method=b.translate_method or None,
        lines=list(b.lines),
        tokens=tokens,
        style=b.style,
    )


def _token_words(bubbles: Sequence[BubbleResult]) -> list[str]:
    return list(dict.fromkeys(str(t["w"]) for b in bubbles for t in b.tokens if t.get("w")))


class JobProcessor:
    """Nhận và xử lý trọn một việc; không bao giờ để lỗi của một trang làm dừng vòng lặp worker."""

    def __init__(
        self,
        jobs: JobQueue,
        storage: FileStorage,
        pipeline: PageProcessor,
        entries: EntryIdLookup,
        clock: Clock,
        cpu: CpuRunner,
    ) -> None:
        self._jobs = jobs
        self._storage = storage
        self._pipeline = pipeline
        self._entries = entries
        self._clock = clock
        self._cpu = cpu

    async def process_next(self, worker_id: str) -> JobOutcome | None:
        """Nhận việc cũ nhất và xử lý; None khi hàng đợi rỗng."""
        job = await self._jobs.claim_next_job(worker_id, self._clock.now())
        if job is None:
            return None
        token = request_id_var.set(f"job-{job.translation_id}")
        try:
            return await self._handle(job)
        finally:
            request_id_var.reset(token)

    async def _handle(self, job: ClaimedJob) -> JobOutcome:
        started = perf_counter()
        log.info("Nhận job %d (lần thử %d)", job.translation_id, job.attempts)
        try:
            n_bubbles, stats = await self._run(job, started)
        except (PipelineStepError, _JobStepError) as exc:
            return await self._fail(job, exc.step, exc.message)
        except Exception:
            log.exception("Job %d lỗi không lường trước", job.translation_id)
            return await self._fail(job, UNKNOWN_STEP, UNKNOWN_MESSAGE)
        log.info(
            "Job %d xong: %d bubble, %d ms, các bước %s",
            job.translation_id,
            n_bubbles,
            _ms(started),
            stats.get("timings_ms", {}),
        )
        return JobOutcome(job.translation_id, ok=True)

    async def _run(self, job: ClaimedJob, started: float) -> tuple[int, dict[str, Any]]:
        image = await self._load(job)
        text = await self._cpu.run(lambda: self._pipeline.process_text(image))
        entry_ids = await self._lookup_entries(text.bubbles)
        bubbles = [to_new_bubble(b, entry_ids) for b in text.bubbles]
        partial = {**text.stats, "mode": text.mode, "n_bubbles": len(bubbles)}
        await self._jobs.save_text_result(job.translation_id, bubbles, partial)
        log.info("Job %d: chữ đã sẵn sàng (%d bubble, %d ms)", job.translation_id, len(bubbles), _ms(started))
        images = await self._cpu.run(lambda: self._pipeline.process_images(text))
        encoded = await self._cpu.run(lambda: _encode_all(image, images))
        inpainted_id = await self._store(encoded.inpainted, FileKind.INPAINTED)
        rendered_id = await self._store(encoded.rendered, FileKind.RENDERED)
        styled = [replace(b, style=images.styles.get(b.idx)) for b in bubbles]
        stats = {**images.stats, "mode": text.mode, "n_bubbles": len(bubbles)}
        await self._jobs.complete_job(
            job.translation_id,
            JobResult(
                bubbles=styled,
                inpainted_file_id=inpainted_id,
                rendered_file_id=rendered_id,
                stats=stats,
                processing_ms=_ms(started),
                phash=encoded.phash,
            ),
        )
        return len(bubbles), stats

    async def _load(self, job: ClaimedJob) -> ImageArray:
        try:
            data = await self._storage.read(job.source_storage_key)
        except NotFoundError as exc:
            raise _JobStepError(LOAD_STEP, "Không còn tệp ảnh gốc") from exc
        image = await self._cpu.run(lambda: decode_image(data))
        if image is None:
            raise _JobStepError(LOAD_STEP, "Không đọc được ảnh gốc (tệp hỏng hoặc sai định dạng)")
        return image

    async def _store(self, data: bytes, kind: FileKind) -> int:
        try:
            return await self._jobs.store_result_image(data, kind)
        except Exception as exc:
            log.exception("Không lưu được ảnh kết quả %s", kind.value)
            raise _JobStepError(STORE_STEP, "Không lưu được ảnh kết quả") from exc

    async def _lookup_entries(self, bubbles: Sequence[BubbleResult]) -> dict[str, int | None]:
        words = _token_words(bubbles)
        try:
            return await self._entries.find_entry_ids(words)
        except Exception:
            # Thiếu entry_id chỉ làm Hover tra lại theo chữ; không đáng để hỏng cả trang.
            log.warning("Tra entry_id cho %d từ lỗi -> để trống", len(words), exc_info=True)
            return {}

    async def _fail(self, job: ClaimedJob, step: str, message: str) -> JobOutcome:
        log.warning("Job %d lỗi ở bước %s: %s", job.translation_id, step, message)
        try:
            status = await self._jobs.fail_job(job.translation_id, step, message)
        except Exception:
            # Việc vẫn `running`; cơ chế nhận lại việc treo (JOB_STALE_MINUTES) sẽ xử lý.
            log.exception("Không ghi được lỗi của job %d", job.translation_id)
            return JobOutcome(job.translation_id, ok=False, error_step=step)
        return JobOutcome(job.translation_id, ok=False, error_step=step, status=status)


def _ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)
