"""Process worker của YingHua: `python -m worker.main` (chạy trong thư mục `server/`).

- `PIPELINE_ENABLED=false`: chỉ chạy tác vụ định kỳ (M15) và heartbeat, không nạp model.
- `PIPELINE_ENABLED=true`: thêm xử lý hàng đợi ảnh (M04) bằng `PipelineAdapter` (YOLO → OCR → dịch → inpaint
  → đắp chữ), model nạp lười ở việc đầu tiên.

Ctrl+C lần 1: dừng êm sau việc đang xử lý. Lần 2: thoát ngay, việc đang `running` được nhận lại sau
`JOB_STALE_MINUTES` (luồng pipeline vẫn chạy nốt trang hiện tại trước khi process kết thúc).
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
from collections.abc import Callable
from dataclasses import dataclass
from types import FrameType

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_session_factory
from app.core.logging import configure_logging
from app.core.storage import LocalFileStorage
from app.modules.imaging.infrastructure.worker import build_worker_jobs
from app.modules.jobs.infrastructure.tasks import build_job_runner
from worker.config import loop_timing_from_settings, pipeline_config_from_settings
from worker.entry_lookup import SqlEntryIdLookup
from worker.job_processor import CpuRunner, JobProcessor, PageProcessor
from worker.loop import WorkerLoop
from worker.pipeline_adapter import PipelineAdapter
from worker.pipeline_types import PipelineConfig

log = logging.getLogger("yinghua.worker")

AdapterFactory = Callable[[PipelineConfig], PageProcessor]
APP_LOGGERS = ("yinghua", "app")


@dataclass(slots=True)
class WorkerApp:
    """Worker đã lắp ghép cùng tài nguyên cần đóng khi thoát."""

    loop: WorkerLoop
    engine: AsyncEngine
    cpu: CpuRunner | None

    async def aclose(self) -> None:
        await self.engine.dispose()
        if self.cpu is not None:
            self.cpu.shutdown()


def make_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def build_worker(
    settings: Settings,
    clock: Clock | None = None,
    adapter_factory: AdapterFactory = PipelineAdapter,
    worker_id: str | None = None,
) -> WorkerApp:
    """Lắp worker từ Settings (cùng CSDL và kho tệp với API); chỉ tạo adapter khi bật pipeline."""
    clock = clock or SystemClock()
    engine = create_engine(settings.database_url, pool_size=settings.db_pool_size, echo=settings.db_echo)
    session_factory = create_session_factory(engine)
    storage = LocalFileStorage(settings.storage_dir / "files")  # cùng gốc với `build_container`
    runner = build_job_runner(session_factory, storage, clock, settings.cleanup_interval_minutes)
    processor: JobProcessor | None = None
    cpu: CpuRunner | None = None
    if settings.pipeline_enabled:
        config = pipeline_config_from_settings(settings)
        log.info("Pipeline bật: thư mục module %s", config.pipeline_dir)
        cpu = CpuRunner()
        processor = JobProcessor(
            jobs=build_worker_jobs(session_factory, storage, clock, settings),
            storage=storage,
            pipeline=adapter_factory(config),
            entries=SqlEntryIdLookup(session_factory),
            clock=clock,
            cpu=cpu,
        )
    loop = WorkerLoop(
        worker_id or make_worker_id(), runner, processor, clock, loop_timing_from_settings(settings)
    )
    return WorkerApp(loop=loop, engine=engine, cpu=cpu)


def _install_signal_handlers(worker: WorkerLoop) -> None:
    event_loop = asyncio.get_running_loop()

    def handle(signum: int, _frame: FrameType | None) -> None:
        if worker.stopping:
            raise KeyboardInterrupt  # lần thứ hai: thoát ngay
        log.info("Nhận tín hiệu %d: dừng sau việc hiện tại (nhấn lần nữa để thoát ngay)", signum)
        event_loop.call_soon_threadsafe(worker.request_stop)

    signal.signal(signal.SIGINT, handle)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle)


async def run_worker(settings: Settings) -> None:
    app = build_worker(settings)
    _install_signal_handlers(app.loop)
    try:
        await app.loop.run()
    finally:
        await app.aclose()


def pin_log_levels(level: str) -> None:
    """Ghim mức log cho logger của YingHua.

    PaddleOCR đặt lại mức root logger thành WARNING khi nạp model, làm mất log INFO của job/heartbeat;
    đặt mức trực tiếp trên logger gốc của ta thì không còn phụ thuộc vào root.
    """
    for name in APP_LOGGERS:
        logging.getLogger(name).setLevel(level.upper())


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    pin_log_levels(settings.log_level)
    try:
        asyncio.run(run_worker(settings))
    except KeyboardInterrupt:
        log.warning("Worker thoát ngay; việc đang chạy (nếu có) sẽ được nhận lại khi quá hạn")


if __name__ == "__main__":
    main()
