"""Vòng lặp worker: xử lý hàng đợi ảnh (nếu bật pipeline), tác vụ định kỳ M15 và heartbeat."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.core.clock import Clock
from worker.config import LoopTiming
from worker.job_processor import JobOutcome, JobProcessor

log = logging.getLogger("yinghua.worker")


class ScheduledJobRunner(Protocol):
    """`JobRunner` của M15."""

    async def run_due_jobs(self, now: datetime, worker_id: str) -> Sequence[Any]: ...


@dataclass(slots=True)
class WorkerCounters:
    done: int = 0
    failed: int = 0


class WorkerLoop:
    """Một worker = một vòng lặp tuần tự. `processor=None` khi `PIPELINE_ENABLED=false` (chỉ chạy lịch)."""

    def __init__(
        self,
        worker_id: str,
        runner: ScheduledJobRunner,
        processor: JobProcessor | None,
        clock: Clock,
        timing: LoopTiming,
    ) -> None:
        self.worker_id = worker_id
        self.counters = WorkerCounters()
        self._runner = runner
        self._processor = processor
        self._clock = clock
        self._timing = timing
        self._stop = asyncio.Event()
        self._last_scheduler: datetime | None = None
        self._last_heartbeat: datetime | None = None

    def request_stop(self) -> None:
        """Dừng êm: việc đang xử lý được làm xong rồi vòng lặp mới thoát."""
        self._stop.set()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    async def run(self) -> None:
        log.info(
            "Worker %s chạy (pipeline %s, hỏi hàng đợi mỗi %.1f s)",
            self.worker_id,
            "bật" if self._processor is not None else "tắt",
            self._timing.poll_seconds,
        )
        while not self.stopping:
            worked = await self.run_once()
            if not worked:
                await self._idle(self._timing.poll_seconds)
        log.info("Worker %s dừng (xong %d, lỗi %d)", self.worker_id, self.counters.done, self.counters.failed)

    async def run_once(self) -> bool:
        """Một nhịp: lịch + heartbeat nếu đến hạn, rồi xử lý tối đa một việc. True nếu vừa xử lý một việc."""
        now = self._clock.now()
        await self._maybe_run_scheduler(now)
        self._maybe_heartbeat(now)
        if self._processor is None or self.stopping:
            return False
        try:
            outcome = await self._processor.process_next(self.worker_id)
        except Exception:
            # Thường do CSDL mất kết nối khi nhận việc; ngủ một nhịp rồi thử lại.
            log.exception("Không nhận được việc từ hàng đợi")
            return False
        if outcome is None:
            return False
        self._count(outcome)
        return True

    def _count(self, outcome: JobOutcome) -> None:
        if outcome.ok:
            self.counters.done += 1
        else:
            self.counters.failed += 1

    def _due(self, last: datetime | None, now: datetime, interval: float) -> bool:
        return last is None or (now - last).total_seconds() >= interval

    async def _maybe_run_scheduler(self, now: datetime) -> None:
        if not self._due(self._last_scheduler, now, self._timing.scheduler_interval_seconds):
            return
        self._last_scheduler = now
        try:
            reports = await self._runner.run_due_jobs(now, self.worker_id)
        except Exception:
            log.exception("Chạy tác vụ định kỳ lỗi")
            return
        if reports:
            log.info("Đã chạy %d tác vụ định kỳ", len(reports))

    def _maybe_heartbeat(self, now: datetime) -> None:
        if not self._due(self._last_heartbeat, now, self._timing.heartbeat_interval_seconds):
            return
        self._last_heartbeat = now
        log.info(
            "Heartbeat worker %s: pipeline=%s, xong=%d, lỗi=%d",
            self.worker_id,
            "bật" if self._processor is not None else "tắt",
            self.counters.done,
            self.counters.failed,
        )

    async def _idle(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return
