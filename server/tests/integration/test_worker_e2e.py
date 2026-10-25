"""Kiểm tra thật: tải trang → worker nhận việc → pipeline thật (YOLO + OCR + dịch) → `done` trên CSDL test.

Mặc định bỏ qua vì nạp model mất vài chục giây. Chạy tay:
    YINGHUA_RUN_WORKER_E2E=1 python -m pytest tests/integration/test_worker_e2e.py -o log_cli=true \
        --log-cli-level=INFO
Ảnh mẫu đổi bằng `YINGHUA_WORKER_E2E_IMAGE`. Chỉ dùng CSDL `*_test` (fixture `test_settings`).
Liên quan F04.07, F04.13, US-XL-07.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest
from fastapi import FastAPI

from app.core.stored_files import FileKind
from app.modules.imaging.application.dto import ClaimedJob, JobResult
from app.modules.imaging.application.worker import WorkerJobs
from app.modules.imaging.domain.entities import TranslationStatus
from app.modules.imaging.infrastructure.worker import build_worker_jobs
from tests.helpers import register
from worker.config import DEFAULT_PIPELINE_DIR, pipeline_config_from_settings
from worker.entry_lookup import SqlEntryIdLookup
from worker.job_processor import CpuRunner, JobProcessor
from worker.main import pin_log_levels
from worker.pipeline_adapter import PipelineAdapter

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("YINGHUA_RUN_WORKER_E2E") != "1", reason="Đặt YINGHUA_RUN_WORKER_E2E=1"
    ),
]

API = "/api/v1"
DEFAULT_IMAGE = DEFAULT_PIPELINE_DIR / "dataset" / "images" / "val" / "trang_001.jpg"
log = logging.getLogger("yinghua.tests.worker_e2e")


class RecordingJobs:
    """Bọc `WorkerJobs` thật để đọc lại kết quả đã ghi."""

    def __init__(self, inner: WorkerJobs) -> None:
        self._inner = inner
        self.result: JobResult | None = None

    async def claim_next_job(self, worker_id: str, now: datetime) -> ClaimedJob | None:
        return await self._inner.claim_next_job(worker_id, now)

    async def store_result_image(self, data: bytes, kind: FileKind) -> int:
        return await self._inner.store_result_image(data, kind)

    async def complete_job(self, translation_id: int, result: JobResult) -> None:
        self.result = result
        await self._inner.complete_job(translation_id, result)

    async def fail_job(self, translation_id: int, error_step: str, error_message: str) -> TranslationStatus:
        return await self._inner.fail_job(translation_id, error_step, error_message)


def _unique_jpeg(path: Path) -> bytes:
    """Đổi một điểm ảnh để sha256 mới: không dùng lại bản dịch `done` của lần chạy trước (F04.14)."""
    img = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    img[0, 0] = np.random.default_rng().integers(0, 256, 3, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    return bytes(buf.tobytes())


async def test_real_pipeline_processes_uploaded_page(app: FastAPI, client: httpx.AsyncClient) -> None:
    image_path = Path(os.environ.get("YINGHUA_WORKER_E2E_IMAGE") or DEFAULT_IMAGE)
    assert image_path.exists(), f"Không thấy ảnh mẫu {image_path}"
    c = app.state.container
    real_jobs = build_worker_jobs(c.session_factory, c.storage, c.clock, c.settings)
    # Đóng việc tồn của các test trước để việc của test này là việc duy nhất trong hàng đợi.
    while (old := await real_jobs.claim_next_job("e2e-drain", datetime.now(timezone.utc))) is not None:
        await real_jobs.fail_job(old.translation_id, "test", "Dọn hàng đợi của test")

    owner = await register(client)
    series = (await client.post(f"{API}/series", json={"title_vi": "E2E"}, headers=owner.headers)).json()
    chapter = (
        await client.post(f"{API}/series/{series['id']}/chapters", json={"number": 1}, headers=owner.headers)
    ).json()
    up = await client.post(
        f"{API}/chapters/{chapter['id']}/pages",
        files=[("files", ("p.jpg", _unique_jpeg(image_path), "image/jpeg"))],
        headers=owner.headers,
    )
    assert up.status_code == 201, up.text
    page_id = up.json()["results"][0]["page"]["id"]

    pin_log_levels("INFO")  # giữ log INFO của worker sau khi PaddleOCR hạ mức root logger
    jobs = RecordingJobs(real_jobs)
    cpu = CpuRunner()
    try:
        processor = JobProcessor(
            jobs,
            c.storage,
            PipelineAdapter(pipeline_config_from_settings(c.settings)),
            SqlEntryIdLookup(c.session_factory),
            c.clock,
            cpu,
        )
        outcome = await processor.process_next("e2e-worker")
    finally:
        cpu.shutdown()

    assert outcome is not None
    assert outcome.ok, f"Job lỗi ở bước {outcome.error_step}"
    status = (await client.get(f"{API}/pages/{page_id}/status", headers=owner.headers)).json()
    assert status["status"] == "done"
    assert jobs.result is not None
    with_entry = sum(1 for b in jobs.result.bubbles for t in b.tokens if t["entry_id"] is not None)
    log.info(
        "E2E: %d bubble, %d token có entry_id, processing_ms=%d, timings_ms=%s",
        len(jobs.result.bubbles),
        with_entry,
        jobs.result.processing_ms,
        jobs.result.stats.get("timings_ms"),
    )
