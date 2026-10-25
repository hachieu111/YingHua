"""Adapter chạy pipeline ảnh: YOLO → OCR → gom dòng + dịch → xóa chữ → đắp chữ → tách từ.

Chuyển từ `Backend/app/services/pipeline_runner.py` (bản cũ), giữ nguyên thuật toán và tham số;
không phụ thuộc CSDL/Settings — worker lắp `PipelineConfig` và tự lưu kết quả.
Model nạp lười một lần cho mỗi adapter; worker chỉ tạo **một** adapter (singleton model AI cho phép).
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from worker import pipeline_assembly as asm
from worker.module_loader import PipelineModules, load_pipeline_modules
from worker.pipeline_types import (
    BubbleResult,
    ImageArray,
    PipelineConfig,
    PipelineResult,
    PipelineStep,
    PipelineStepError,
)
from worker.text_segmenter import tokenize_chinese

__all__ = ["BubbleResult", "PipelineAdapter", "PipelineConfig", "PipelineResult", "PipelineStepError"]

log = logging.getLogger("yinghua.worker.pipeline")

# Tham số xóa chữ đã dùng ổn định ở bản cũ (main.py /process-page) — không đổi.
TEXT_DILATE_PX = 5
BUBBLE_ERODE_PX = 12

_STEP_MESSAGES: dict[PipelineStep, str] = {
    "detect": "Lỗi khi nhận diện bong bóng",
    "ocr": "Lỗi khi nhận dạng chữ (OCR)",
    "segment": "Lỗi khi tách từ",
    "translate": "Lỗi khi dịch",
    "inpaint": "Lỗi khi xóa chữ gốc",
    "render": "Lỗi khi đắp chữ tiếng Việt",
}


def _step_error(step: PipelineStep, exc: Exception) -> PipelineStepError:
    log.error("Bước %s lỗi", step, exc_info=exc)
    return PipelineStepError(step, f"{_STEP_MESSAGES[step]} ({type(exc).__name__})")


def _ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


class _TimedCall:
    """Bọc `engine.detect_bubbles` để đo riêng bước detect và biết lỗi rơi vào detect hay OCR."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func
        self.finished = False
        self.elapsed_ms = 0

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        start = perf_counter()
        try:
            result = self._func(*args, **kwargs)
        finally:
            self.elapsed_ms = _ms(start)
        self.finished = True
        return result


@dataclass(slots=True)
class _Translated:
    bubble_id: int
    regions: list[dict[str, Any]]
    payload: dict[str, Any]


class _PageRun:
    """Trạng thái một lần xử lý trang (một ảnh)."""

    def __init__(self, mods: PipelineModules, img: ImageArray) -> None:
        self.mods = mods
        self.img = img
        self.timings: dict[str, int] = {}

    @contextmanager
    def step(self, name: PipelineStep) -> Iterator[None]:
        start = perf_counter()
        try:
            yield
        except PipelineStepError:
            raise
        except Exception as exc:
            raise _step_error(name, exc) from exc
        finally:
            self.timings[name] = _ms(start)
            log.debug("Bước %s: %d ms", name, self.timings[name])

    def detect_and_ocr(self) -> dict[str, Any]:
        engine = self.mods.engine
        had_own = "detect_bubbles" in vars(engine)
        original = engine.detect_bubbles
        probe = _TimedCall(original)
        engine.detect_bubbles = probe
        start = perf_counter()
        try:
            ocr: dict[str, Any] = engine.process(self.img, detect_floating=False)
            return ocr
        except Exception as exc:
            raise _step_error("ocr" if probe.finished else "detect", exc) from exc
        finally:
            if had_own:
                engine.detect_bubbles = original
            else:
                del engine.detect_bubbles
            self.timings["detect"] = probe.elapsed_ms
            self.timings["ocr"] = max(_ms(start) - probe.elapsed_ms, 0)

    def translate(self, texts: list[dict[str, Any]]) -> list[_Translated]:
        out: list[_Translated] = []
        with self.step("translate"):
            for bid, regions in asm.group_by_bubble(texts).items():
                lines, kept = asm.order_and_dedupe(regions)
                full = "".join(lines)
                if not full.strip():
                    continue
                tr = self.mods.translator.translate(full)
                payload = {
                    "text_zh": tr["original"],
                    "pinyin": tr["pinyin"],
                    "vi": tr["vi"],
                    "method": tr["method"],
                    "bubble_id": bid,
                }
                out.append(_Translated(bid, kept, payload))
        return out

    def inpaint(self, texts: list[dict[str, Any]], bubbles: list[dict[str, Any]]) -> dict[str, Any]:
        with self.step("inpaint"):
            # Hàm của module luôn ghi một file vào dataset/inpainted → đặt tên ngẫu nhiên rồi xóa ngay.
            inp: dict[str, Any] = self.mods.process_and_save(
                img=self.img,
                text_regions=texts,
                bubbles=bubbles,
                original_filename=f"job_{uuid.uuid4().hex[:12]}.jpg",
                text_dilate_px=TEXT_DILATE_PX,
                bubble_erode_px=BUBBLE_ERODE_PX,
            )
        _remove_scratch_file(inp.get("saved_path"))
        return inp

    def render(
        self,
        inpainted: ImageArray,
        ocr: dict[str, Any],
        texts: list[dict[str, Any]],
        translated: list[_Translated],
    ) -> ImageArray:
        with self.step("render"):
            rendered: ImageArray = self.mods.render_all_bubbles(
                img=inpainted,
                bubbles=ocr["bubbles"],
                texts=texts,
                bubble_translations={t.bubble_id: t.payload for t in translated},
                original_img=self.img,
            )
        return rendered

    def tokenize(self, translated: list[_Translated]) -> dict[int, list[dict[str, Any]]]:
        with self.step("segment"):
            return {t.bubble_id: tokenize_chinese(t.payload["text_zh"]) for t in translated}

    def style_of(
        self, inpainted: ImageArray, t: _Translated, bubble: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not bubble:
            return None
        try:
            style: dict[str, Any] = asm.jsonable(
                self.mods.extract_style(inpainted, t.regions, bubble, original_img=self.img)
            )
            return style
        except Exception:
            # Style chỉ là gợi ý hiển thị; thiếu style không làm hỏng trang (giữ như bản cũ).
            log.debug("extract_style lỗi ở bubble %s", t.bubble_id, exc_info=True)
            return None


def _remove_scratch_file(saved_path: str | None) -> None:
    if not saved_path:
        return
    try:
        Path(saved_path).unlink(missing_ok=True)
    except OSError:
        log.warning("Không xóa được file tạm của inpainter: %s", saved_path, exc_info=True)


def _build_bubble(
    run: _PageRun,
    t: _Translated,
    bubbles: list[dict[str, Any]],
    inpainted: ImageArray,
    tokens: list[dict[str, Any]],
) -> BubbleResult:
    b = asm.find_bubble(bubbles, t.bubble_id)
    x, y, w, h = asm.bubble_box(b, t.regions)
    return BubbleResult(
        idx=t.bubble_id,
        class_name=asm.normalize_class_name(b.get("class_name", asm.DEFAULT_CLASS)),
        x=x,
        y=y,
        w=w,
        h=h,
        polygon=asm.jsonable(b.get("polygon")) if b else None,
        confidence=asm.jsonable(b.get("confidence")),
        text_zh=t.payload["text_zh"],
        pinyin=t.payload["pinyin"],
        text_vi=t.payload["vi"],
        translate_method=t.payload["method"],
        lines=asm.build_lines(t.regions),
        tokens=tokens,
        style=run.style_of(inpainted, t, b),
    )


def _validate_image(image_bgr: Any) -> None:
    if not isinstance(image_bgr, np.ndarray) or image_bgr.ndim != 3 or image_bgr.size == 0:
        raise PipelineStepError("detect", "Ảnh đầu vào không hợp lệ hoặc rỗng")


class PipelineAdapter:
    """Chạy pipeline ảnh cho một trang; an toàn khi gọi từ thread worker (tuần tự hóa bằng khóa)."""

    def __init__(
        self,
        config: PipelineConfig,
        loader: Callable[[PipelineConfig], PipelineModules] = load_pipeline_modules,
    ) -> None:
        self._config = config
        self._loader = loader
        self._mods: PipelineModules | None = None
        self._lock = threading.Lock()
        self.load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._mods is not None

    def _ensure_loaded(self) -> PipelineModules:
        if self._mods is None:
            try:
                self._mods = self._loader(self._config)
                self.load_error = None
            except PipelineStepError as exc:
                self.load_error = exc.message
                raise
        return self._mods

    def process(self, image_bgr: ImageArray) -> PipelineResult:
        """Xử lý một ảnh BGR; lỗi ở bước nào ném `PipelineStepError` của bước đó."""
        _validate_image(image_bgr)
        with self._lock:
            return self._run(_PageRun(self._ensure_loaded(), image_bgr))

    def _run(self, run: _PageRun) -> PipelineResult:
        started = perf_counter()
        ocr = run.detect_and_ocr()
        bubbles: list[dict[str, Any]] = ocr["bubbles"]
        texts = asm.select_bubble_texts(ocr["texts"])
        translated = run.translate(texts)
        inp = run.inpaint(texts, bubbles)
        inpainted: ImageArray = inp["inpainted_img"]
        rendered = run.render(inpainted, ocr, texts, translated)
        tokens = run.tokenize(translated)
        results = [_build_bubble(run, t, bubbles, inpainted, tokens[t.bubble_id]) for t in translated]
        run.timings["total"] = _ms(started)
        stats = asm.jsonable(
            {
                **ocr.get("stats", {}),
                "n_inpainted": inp.get("n_regions", 0),
                "n_translated": len(translated),
                "timings_ms": run.timings,
            }
        )
        log.info("Trang xong: %d bubble, mode=%s, %d ms", len(results), ocr.get("mode"), run.timings["total"])
        return PipelineResult(
            bubbles=results, inpainted=inpainted, rendered=rendered, mode=ocr.get("mode"), stats=stats
        )
