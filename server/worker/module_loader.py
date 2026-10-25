"""Nạp module `module xử lí ảnh/.../src` và trỏ lại các đường dẫn hardcode (không sửa code module).

Giống `PipelineWorker._load` của bản cũ: chỉnh `pipeline.YOLO_MODEL_PATH`, font của `text_renderer`
và đường dẫn từ điển của `translator` **trước** khi tạo singleton `get_pipeline()` / `get_translator()`.
"""

from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from worker.pipeline_types import PipelineConfig, PipelineStep, PipelineStepError

log = logging.getLogger("yinghua.worker.pipeline")

_MODULE_NAMES = ("pipeline", "text_renderer", "translator", "inpainter")


@dataclass(slots=True)
class PipelineModules:
    """Các đối tượng/hàm của module ảnh mà adapter cần (đã khởi tạo)."""

    engine: Any
    translator: Any
    process_and_save: Callable[..., dict[str, Any]]
    render_all_bubbles: Callable[..., Any]
    extract_style: Callable[..., Any]


def _import_modules(pipeline_dir: Path) -> dict[str, ModuleType]:
    src = str(pipeline_dir / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    try:
        return {name: importlib.import_module(name) for name in _MODULE_NAMES}
    except Exception as exc:
        log.error("Không import được module xử lý ảnh từ %s", src, exc_info=True)
        raise PipelineStepError("detect", f"Không nạp được module xử lý ảnh ({type(exc).__name__})") from exc


def _point_yolo(pl: Any, model_path: Path) -> None:
    # Module ảnh được gõ `Any`: ta gán lại thuộc tính đường dẫn hardcode mà mypy không biết.
    if model_path.exists():
        pl.YOLO_MODEL_PATH = str(model_path)
    else:
        log.warning("Không thấy model YOLO tại %s -> pipeline chạy chế độ ocr_only_fallback", model_path)


def _point_fonts(tr: Any, font_dir: Path) -> None:
    if not font_dir.exists():
        log.warning("Không thấy thư mục font %s -> dùng font mặc định", font_dir)
        return
    old_base = tr._FONT_BASE
    tr._FONT_PATHS = {k: font_dir / Path(v).relative_to(old_base) for k, v in tr._FONT_PATHS.items()}
    tr._FONT_BASE = font_dir
    tr._font_cache.clear()


def _point_dictionaries(trn: Any, dict_dir: Path) -> None:
    if not dict_dir.exists():
        log.warning("Không thấy thư mục từ điển tu tiên %s -> bản dịch có thể thiếu", dict_dir)
    trn.DICT_DIR = dict_dir
    trn.NAMES_FILE = dict_dir / "Names.txt"
    trn.VIETPHRASE_FILE = dict_dir / "VietPhrase.txt"
    trn.LUATNHAN_FILE = dict_dir / "LuatNhan.txt"
    trn.PHIENAM_FILE = dict_dir / "PhienAm.txt"


def _build(factory: Callable[[], Any], step: PipelineStep, message: str) -> Any:
    try:
        return factory()
    except Exception as exc:
        log.error("%s", message, exc_info=True)
        raise PipelineStepError(step, f"{message} ({type(exc).__name__})") from exc


def load_pipeline_modules(config: PipelineConfig) -> PipelineModules:
    """Nạp YOLO + PaddleOCR + bộ dịch (rất nặng, gọi một lần)."""
    mods = _import_modules(config.pipeline_dir)
    _point_yolo(mods["pipeline"], config.yolo_model_path)
    _point_fonts(mods["text_renderer"], config.font_dir)
    _point_dictionaries(mods["translator"], config.xianxia_dict_dir)
    log.info("Đang nạp pipeline (YOLO + PaddleOCR) và bộ dịch tu tiên...")
    engine = _build(mods["pipeline"].get_pipeline, "detect", "Không nạp được mô hình nhận diện/OCR")
    translator = _build(mods["translator"].get_translator, "translate", "Không nạp được bộ từ điển dịch")
    log.info("Pipeline sẵn sàng")
    return PipelineModules(
        engine=engine,
        translator=translator,
        process_and_save=mods["inpainter"].process_and_save,
        render_all_bubbles=mods["text_renderer"].render_all_bubbles,
        extract_style=mods["text_renderer"].extract_style,
    )
