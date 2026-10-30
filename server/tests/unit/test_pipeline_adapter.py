"""Test adapter pipeline ảnh của worker bằng fake (không nạp YOLO/PaddleOCR).

Liên quan F04 (xử lý ảnh), US-QT-07 (job lỗi có lý do đọc được).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from worker import pipeline_adapter as pa
from worker import pipeline_assembly as asm
from worker.module_loader import PipelineModules, load_pipeline_modules
from worker.pipeline_adapter import PipelineAdapter, PipelineConfig, PipelineStepError

IMG = np.zeros((40, 60, 3), dtype=np.uint8)


def _region(text: str, bid: int, x: int, y: int, w: int = 10, h: int = 10) -> dict[str, Any]:
    return {
        "text": text,
        "bubble_id": bid,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "polygon": np.array([[x, y], [x + w, y]]),
        "confidence": np.float32(0.9),
    }


def _default_texts() -> list[dict[str, Any]]:
    return [
        _region("世界", 0, 0, 20),
        _region("你好", 0, 5, 0),
        _region("你好", 0, 6, 1),  # trùng liền kề sau khi sắp (y, x) → bỏ
        _region("  ", 0, 0, 30),
        _region("砰", 1, 30, 5, w=8, h=30),
        _region("迷路", 5, 40, 10, w=5, h=12),  # bubble_id ngoài danh sách → khung bao
        _region("飘", -1, 0, 0),  # chữ trôi nổi → bỏ
    ]


class FakeEngine:
    def __init__(self, texts: list[dict[str, Any]] | None = None, fail: str | None = None) -> None:
        self.texts = _default_texts() if texts is None else texts
        self.fail = fail
        self.bubbles = [
            {
                "x": np.int64(1),
                "y": 2,
                "w": 30,
                "h": 25,
                "class_name": "weird_class",
                "confidence": np.float32(0.75),
                "polygon": np.array([[1, 2], [31, 27]]),
            },
            {
                "x": 28,
                "y": 3,
                "w": 12,
                "h": 34,
                "class_name": "sound_effect",
                "confidence": 0.5,
                "polygon": [[28, 3]],
            },
        ]

    def detect_bubbles(self, img: Any) -> list[dict[str, Any]]:
        if self.fail == "detect":
            raise RuntimeError("yolo nổ")
        return self.bubbles

    def process(self, img: Any, detect_floating: bool = True) -> dict[str, Any]:
        assert detect_floating is False
        bubbles = self.detect_bubbles(img)
        if self.fail == "ocr":
            raise RuntimeError("paddle nổ")
        return {
            "mode": "yolo_segmentation+ocr",
            "bubbles": bubbles,
            "texts": self.texts,
            "stats": {"speech_bubble": np.int64(3), "total": 7},
        }


class FakeTranslator:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[str] = []

    def translate(self, text: str) -> dict[str, Any]:
        if self.fail:
            raise ValueError("dict lỗi")
        self.calls.append(text)
        return {"original": text, "pinyin": f"py:{text}", "vi": f"vi:{text}", "method": "fake"}


class FakeModules:
    def __init__(self, tmp_path: Path, fail: str | None = None) -> None:
        self.fail = fail
        self.engine = FakeEngine(fail=fail)
        self.translator = FakeTranslator(fail=fail == "translate")
        self.tmp_path = tmp_path
        self.saved: Path | None = None
        self.inpaint_kwargs: dict[str, Any] = {}
        self.render_kwargs: dict[str, Any] = {}

    def process_and_save(self, **kwargs: Any) -> dict[str, Any]:
        if self.fail == "inpaint":
            raise MemoryError()
        self.inpaint_kwargs = kwargs
        self.saved = self.tmp_path / kwargs["original_filename"]
        self.saved.write_bytes(b"x")
        return {"inpainted_img": kwargs["img"].copy(), "saved_path": str(self.saved), "n_regions": 2}

    def render_all_bubbles(self, **kwargs: Any) -> Any:
        if self.fail == "render":
            raise OSError("font hỏng")
        self.render_kwargs = kwargs
        return kwargs["img"].copy()

    def extract_style(self, img: Any, regions: Any, bubble: Any, original_img: Any = None) -> Any:
        if bubble["class_name"] == "sound_effect":
            raise KeyError("style lỗi")  # bị nuốt có log, style = None
        return {"color": np.array([1, 2, 3]), "size": np.float32(12.0), "pos": (1, 2)}

    def as_modules(self) -> PipelineModules:
        return PipelineModules(
            self.engine, self.translator, self.process_and_save, self.render_all_bubbles, self.extract_style
        )


CONFIG = PipelineConfig(Path("p"), Path("m.pt"), Path("f"), Path("d"))


def _adapter(fake: FakeModules) -> PipelineAdapter:
    return PipelineAdapter(CONFIG, loader=lambda _cfg: fake.as_modules())


def _by_idx(result: pa.PipelineResult) -> dict[int, pa.BubbleResult]:
    return {b.idx: b for b in result.bubbles}


def test_process_groups_lines_by_position_and_drops_consecutive_duplicates(tmp_path: Path) -> None:
    fake = FakeModules(tmp_path)
    bubbles = _by_idx(_adapter(fake).process(IMG))
    assert set(bubbles) == {0, 1, 5}  # chữ trôi nổi (-1) bị bỏ
    assert bubbles[0].text_zh == "你好世界"
    assert [ln["text"] for ln in bubbles[0].lines] == ["你好", "世界"]
    assert bubbles[0].text_vi == "vi:你好世界"
    assert bubbles[0].translate_method == "fake"
    assert fake.translator.calls == ["你好世界", "砰", "迷路"]  # dịch cả câu, một lần mỗi bong bóng


def test_process_normalizes_class_name_to_valid_classes(tmp_path: Path) -> None:
    bubbles = _by_idx(_adapter(FakeModules(tmp_path)).process(IMG))
    assert bubbles[0].class_name == "speech_bubble"
    assert bubbles[1].class_name == "sound_effect"
    assert bubbles[5].class_name == "speech_bubble"
    assert asm.normalize_class_name(None) == "speech_bubble"
    assert asm.normalize_class_name("floating_text") == "floating_text"


def test_process_uses_line_bounding_box_when_bubble_missing(tmp_path: Path) -> None:
    bubbles = _by_idx(_adapter(FakeModules(tmp_path)).process(IMG))
    b = bubbles[5]
    assert (b.x, b.y, b.w, b.h) == (40, 10, 5, 12)
    assert b.polygon is None and b.confidence is None and b.style is None
    assert (bubbles[0].x, bubbles[0].y, bubbles[0].w, bubbles[0].h) == (1, 2, 30, 25)


def test_process_marks_tall_multi_char_lines_vertical() -> None:
    assert asm.is_vertical({"text": "砰砰", "w": 8, "h": 30}) is True
    assert asm.is_vertical({"text": "砰", "w": 8, "h": 30}) is False
    assert asm.is_vertical({"text": "你好", "w": 30, "h": 10}) is False


def test_process_output_is_plain_json(tmp_path: Path) -> None:
    result = _adapter(FakeModules(tmp_path)).process(IMG)
    payload = {"bubbles": [b.to_dict() for b in result.bubbles], "stats": result.stats, "mode": result.mode}
    json.dumps(payload)  # không được ném TypeError với numpy
    b0 = _by_idx(result)[0]
    assert type(b0.confidence) is float
    assert b0.polygon == [[1, 2], [31, 27]]
    assert b0.style == {"color": [1, 2, 3], "size": 12.0, "pos": [1, 2]}
    assert type(b0.lines[0]["confidence"]) is float
    assert result.stats["speech_bubble"] == 3


def test_process_reports_stats_timings_and_mode(tmp_path: Path) -> None:
    result = _adapter(FakeModules(tmp_path)).process(IMG)
    assert result.mode == "yolo_segmentation+ocr"
    assert result.stats["n_inpainted"] == 2
    assert result.stats["n_translated"] == 3
    assert set(result.stats["timings_ms"]) == {
        "detect",
        "ocr",
        "translate",
        "inpaint",
        "render",
        "segment",
        "total",
    }


def test_two_phases_text_first_without_style_then_images_with_style(tmp_path: Path) -> None:
    """F04.02: giai đoạn chữ không chạm inpaint/render; giai đoạn ảnh trả style theo idx."""
    fake = FakeModules(tmp_path)
    adapter = _adapter(fake)
    text = adapter.process_text(IMG)
    assert {b.idx for b in text.bubbles} == {0, 1, 5} and all(b.style is None for b in text.bubbles)
    assert fake.saved is None and not fake.render_kwargs  # chưa xóa chữ/đắp chữ
    assert set(text.stats["timings_ms"]) == {"detect", "ocr", "translate", "segment"}
    images = adapter.process_images(text)
    assert images.styles[0] == {"color": [1, 2, 3], "size": 12.0, "pos": [1, 2]}
    assert set(images.stats["timings_ms"]) == {
        "detect",
        "ocr",
        "translate",
        "segment",
        "inpaint",
        "render",
        "total",
    }


def test_process_passes_original_params_and_removes_scratch_file(tmp_path: Path) -> None:
    fake = FakeModules(tmp_path)
    _adapter(fake).process(IMG)
    assert fake.inpaint_kwargs["text_dilate_px"] == 5
    assert fake.inpaint_kwargs["bubble_erode_px"] == 12
    assert len(fake.inpaint_kwargs["text_regions"]) == 6  # mọi dòng của bong bóng, kể cả dòng trùng
    assert fake.saved is not None and not fake.saved.exists()
    assert set(fake.render_kwargs["bubble_translations"]) == {0, 1, 5}
    assert fake.render_kwargs["original_img"] is IMG


def test_process_restores_engine_detect_method(tmp_path: Path) -> None:
    fake = FakeModules(tmp_path)
    _adapter(fake).process(IMG)
    assert "detect_bubbles" not in vars(fake.engine)


def test_process_tokens_keep_only_chinese_with_pinyin(tmp_path: Path) -> None:
    fake = FakeModules(tmp_path)
    fake.engine.texts = [_region("你好，世界！", 0, 0, 0)]
    tokens = _adapter(fake).process(IMG).bubbles[0].tokens
    assert [t["w"] for t in tokens] == ["你好", "世界"]
    assert tokens[0] == {"w": "你好", "start": 0, "end": 2, "pinyin": "nǐ hǎo"}
    assert all("entry_id" not in t for t in tokens)


@pytest.mark.parametrize("step", ["detect", "ocr", "translate", "inpaint", "render"])
def test_process_maps_step_failure_to_pipeline_step_error(tmp_path: Path, step: str) -> None:
    fake = FakeModules(tmp_path, fail=step)
    with pytest.raises(PipelineStepError) as info:
        _adapter(fake).process(IMG)
    assert info.value.step == step
    assert "Traceback" not in info.value.message
    assert "detect_bubbles" not in vars(fake.engine)


def test_process_maps_tokenizer_failure_to_segment_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_text: str) -> list[dict[str, Any]]:
        raise RuntimeError("jieba lỗi")

    monkeypatch.setattr(pa, "tokenize_chinese", boom)
    with pytest.raises(PipelineStepError) as info:
        _adapter(FakeModules(tmp_path)).process(IMG)
    assert info.value.step == "segment"
    assert info.value.message == "Lỗi khi tách từ (RuntimeError)"


def test_process_rejects_invalid_image(tmp_path: Path) -> None:
    with pytest.raises(PipelineStepError) as info:
        _adapter(FakeModules(tmp_path)).process(np.zeros((0, 0, 3), dtype=np.uint8))
    assert info.value.step == "detect"


def test_adapter_loads_once_and_retries_after_load_failure(tmp_path: Path) -> None:
    fake = FakeModules(tmp_path)
    calls: list[int] = []

    def loader(_cfg: PipelineConfig) -> PipelineModules:
        calls.append(1)
        if len(calls) == 1:
            raise PipelineStepError("detect", "Không nạp được mô hình nhận diện/OCR (OSError)")
        return fake.as_modules()

    adapter = PipelineAdapter(CONFIG, loader=loader)
    with pytest.raises(PipelineStepError):
        adapter.process(IMG)
    assert adapter.load_error and not adapter.is_loaded
    adapter.process(IMG)
    adapter.process(IMG)
    assert len(calls) == 2 and adapter.is_loaded and adapter.load_error is None


def _fake_module(name: str, **attrs: Any) -> ModuleType:
    mod = ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def test_loader_points_hardcoded_paths_before_building_singletons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.pt"
    model.write_bytes(b"")
    fonts, dicts = tmp_path / "fonts", tmp_path / "dict"
    fonts.mkdir()
    dicts.mkdir()
    old_base = Path("old_fonts")
    seen: dict[str, Any] = {}
    pl = _fake_module("pipeline", YOLO_MODEL_PATH="cũ")
    pl.get_pipeline = lambda: seen.setdefault("yolo", pl.YOLO_MODEL_PATH)
    tr = _fake_module(
        "text_renderer",
        _FONT_BASE=old_base,
        _font_cache={"x": 1},
        _FONT_PATHS={"dialogue": old_base / "HL" / "a.ttf"},
        render_all_bubbles=lambda **k: None,
        extract_style=lambda *a, **k: None,
    )
    trn = _fake_module("translator")
    trn.get_translator = lambda: seen.setdefault("names", trn.NAMES_FILE)
    inp = _fake_module("inpainter", process_and_save=lambda **k: {})
    for mod in (pl, tr, trn, inp):
        monkeypatch.setitem(sys.modules, mod.__name__, mod)
    monkeypatch.setattr(sys, "path", list(sys.path))

    load_pipeline_modules(PipelineConfig(tmp_path / "pipe", model, fonts, dicts))

    assert seen == {"yolo": str(model), "names": dicts / "Names.txt"}
    font_paths, font_base, vietphrase = tr._FONT_PATHS, tr._FONT_BASE, trn.VIETPHRASE_FILE
    assert font_paths == {"dialogue": fonts / "HL" / "a.ttf"}
    assert font_base == fonts
    assert tr._font_cache == {}
    assert vietphrase == dicts / "VietPhrase.txt"
    assert sys.path[0] == str(tmp_path / "pipe" / "src")


# ---------------------------------------------------------------- chạy tay với model thật
_MODULE_DIR = Path(__file__).resolve().parents[3] / "module xử lí ảnh"
_PIPELINE_DIR = _MODULE_DIR / "mudule xu ly anh"
_SAMPLE = _PIPELINE_DIR / "dataset" / "images" / "val" / "trang_001.jpg"


@pytest.mark.skipif(
    os.environ.get("YINGHUA_RUN_REAL_PIPELINE") != "1" or not _SAMPLE.exists(),
    reason="Chạy tay: đặt YINGHUA_RUN_REAL_PIPELINE=1 (nạp YOLO + PaddleOCR thật, rất chậm)",
)
def test_real_pipeline_processes_sample_page() -> None:
    import cv2

    img = cv2.imdecode(np.fromfile(str(_SAMPLE), dtype=np.uint8), cv2.IMREAD_COLOR)
    adapter = PipelineAdapter(
        PipelineConfig(
            pipeline_dir=_PIPELINE_DIR,
            yolo_model_path=_PIPELINE_DIR / "models bong bóng" / "model.pt",
            font_dir=_MODULE_DIR / "font chữ" / "Font-chu-truyen-tranh-Comic" / "Font chữ truyện tranh Comic",
            xianxia_dict_dir=_MODULE_DIR / "từ điển tu tiên",
        )
    )
    start = time.perf_counter()
    result = adapter.process(img)
    elapsed = time.perf_counter() - start
    json.dumps([b.to_dict() for b in result.bubbles])
    json.dumps(result.stats)
    assert result.rendered.shape == img.shape
    assert all(b.class_name in asm.VALID_CLASSES for b in result.bubbles)
    sys.stderr.write(
        f"\nREAL: {len(result.bubbles)} bubble, mode={result.mode}, {elapsed:.1f}s, stats={result.stats}\n"
    )
