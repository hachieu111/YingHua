"""Cấu hình riêng của worker: nhịp vòng lặp và đường dẫn tài nguyên pipeline lấy từ `Settings`.

Đường dẫn (`PIPELINE_DIR`, `YOLO_MODEL_PATH`, `FONT_DIR`, `XIANXIA_DICT_DIR`) và `WORKER_POLL_SECONDS` đọc từ
biến môi trường / `server/.env` qua `Settings`; mặc định trỏ vào thư mục `module xử lí ảnh/` ở gốc repo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import DEFAULT_PIPELINE_DIR, Settings
from worker.pipeline_types import PipelineConfig

__all__ = ["DEFAULT_PIPELINE_DIR", "LoopTiming", "loop_timing_from_settings", "pipeline_config_from_settings"]

SCHEDULER_INTERVAL_SECONDS = 30.0  # gọi `run_due_jobs` (M15) tối đa mỗi chừng này
HEARTBEAT_INTERVAL_SECONDS = 60.0  # log INFO trạng thái worker


@dataclass(frozen=True, slots=True)
class LoopTiming:
    poll_seconds: float = 3.0  # hàng đợi rỗng → ngủ chừng này rồi hỏi lại
    scheduler_interval_seconds: float = SCHEDULER_INTERVAL_SECONDS
    heartbeat_interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS


def pipeline_config_from_settings(settings: Settings) -> PipelineConfig:
    return PipelineConfig(
        pipeline_dir=settings.pipeline_dir,
        yolo_model_path=settings.yolo_model_path,
        font_dir=settings.font_dir,
        xianxia_dict_dir=settings.xianxia_dict_dir,
    )


def loop_timing_from_settings(settings: Settings) -> LoopTiming:
    return LoopTiming(poll_seconds=settings.worker_poll_seconds)
