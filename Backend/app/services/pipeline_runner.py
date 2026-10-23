"""Worker nền chạy pipeline của module xử lí ảnh (YOLO -> PaddleOCR -> dịch -> xoá chữ -> đắp chữ).

- Một thread duy nhất (model không thread-safe, chạy CPU), nhận translation_id từ hàng đợi.
- Không sửa code module: chỉ trỏ lại các đường dẫn hardcode (model YOLO, font, từ điển tu tiên)
  trước khi khởi tạo singleton.
- Logic gom dòng theo bubble / dịch / inpaint / render giữ đúng như POST /process-page trong main.py.
"""

import json
import logging
import queue
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update

from ..config import settings
from ..db import SessionLocal
from ..models import Bubble, Translation
from . import dictionary, storage

log = logging.getLogger("yinghua.pipeline")

VALID_CLASSES = {"speech_bubble", "sound_effect", "calligraphy", "floating_text"}


def _jsonable(obj):
    """Đổi numpy/tuple về kiểu JSON thuần (style từ extract_style có thể chứa numpy)."""
    return json.loads(json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else
                                 (o.tolist() if hasattr(o, "tolist") else str(o))))


class PipelineWorker:
    def __init__(self):
        self.q: "queue.Queue[int]" = queue.Queue()
        self.thread: threading.Thread | None = None
        self.loaded = False
        self.load_error: str | None = None
        self.current: int | None = None
        self._mods = {}

    # ---------------------------------------------------------- lifecycle
    def start(self):
        if not settings.pipeline_enabled or self.thread is not None:
            return
        # Job đang chạy dở khi server tắt -> chạy lại
        with SessionLocal() as db:
            db.execute(update(Translation).where(Translation.status == "running").values(status="queued"))
            db.commit()
            for (tid,) in db.execute(select(Translation.id).where(Translation.status == "queued")
                                     .order_by(Translation.id)).all():
                self.q.put(tid)
        self.thread = threading.Thread(target=self._loop, name="pipeline-worker", daemon=True)
        self.thread.start()

    def enqueue(self, translation_id: int):
        if settings.pipeline_enabled:
            self.q.put(translation_id)

    def status(self) -> dict:
        return {"enabled": settings.pipeline_enabled, "loaded": self.loaded, "load_error": self.load_error,
                "queue_size": self.q.qsize(), "current": self.current}

    # ---------------------------------------------------------- loading
    def _load(self):
        if self.loaded:
            return
        src = str(Path(settings.pipeline_dir) / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        import pipeline as pl          # noqa: E402  (module của bạn)
        import text_renderer as tr
        import translator as trn
        import inpainter as inp

        if settings.yolo_model_path.exists():
            pl.YOLO_MODEL_PATH = str(settings.yolo_model_path)
        else:
            log.warning("Không thấy model YOLO tại %s -> pipeline chạy chế độ ocr_only_fallback",
                        settings.yolo_model_path)

        if settings.font_dir.exists():
            old_base = tr._FONT_BASE
            tr._FONT_PATHS = {k: settings.font_dir / Path(v).relative_to(old_base) for k, v in tr._FONT_PATHS.items()}
            tr._FONT_BASE = settings.font_dir
            tr._font_cache.clear()
        else:
            log.warning("Không thấy thư mục font %s -> dùng font mặc định", settings.font_dir)

        d = settings.xianxia_dict_dir
        trn.DICT_DIR = d
        trn.NAMES_FILE = d / "Names.txt"
        trn.VIETPHRASE_FILE = d / "VietPhrase.txt"
        trn.LUATNHAN_FILE = d / "LuatNhan.txt"
        trn.PHIENAM_FILE = d / "PhienAm.txt"

        log.info("Đang nạp pipeline (YOLO + PaddleOCR) và bộ dịch tu tiên...")
        self._mods = {
            "pipeline": pl.get_pipeline(),
            "translator": trn.get_translator(),
            "process_and_save": inp.process_and_save,
            "render_all_bubbles": tr.render_all_bubbles,
            "extract_style": tr.extract_style,
        }
        self.loaded = True
        log.info("Pipeline sẵn sàng")

    # ---------------------------------------------------------- loop
    def _loop(self):
        while True:
            tid = self.q.get()
            self.current = tid
            try:
                self._load()
                self._process(tid)
            except Exception as exc:  # lỗi nạp model hoặc lỗi bất ngờ
                if not self.loaded:
                    self.load_error = f"{type(exc).__name__}: {exc}"
                log.exception("Translation %s lỗi", tid)
                self._mark_failed(tid, traceback.format_exc())
            finally:
                self.current = None
                self.q.task_done()

    def _mark_failed(self, tid: int, err: str):
        with SessionLocal() as db:
            t = db.get(Translation, tid)
            if t is not None:
                t.status = "failed"
                t.error = err[-4000:]
                t.finished_at = datetime.now(timezone.utc)
                db.commit()

    # ---------------------------------------------------------- one job
    def _process(self, tid: int):
        m = self._mods
        started = time.perf_counter()
        with SessionLocal() as db:
            t = db.get(Translation, tid)
            if t is None or t.status not in ("queued", "failed"):
                return
            t.status = "running"
            t.error = None
            db.commit()

            src_file = db.get(storage.StoredFile, t.source_file_id) if t.source_file_id else None
            img = storage.read_image(src_file) if src_file else None
            if img is None:
                raise RuntimeError("Không đọc được ảnh gốc (file đã hết hạn hoặc bị xoá)")
            expires = src_file.expires_at

            # Stage 1+2: YOLO -> OCR (bỏ floating text, như main.py)
            ocr = m["pipeline"].process(img, detect_floating=False)
            bubbles = ocr["bubbles"]
            texts = [x for x in ocr["texts"] if x.get("bubble_id", -1) >= 0]

            # Stage 3: gom dòng theo bubble, dịch cả câu
            grouped: dict[int, list] = {}
            for x in texts:
                grouped.setdefault(x["bubble_id"], []).append(x)
            translations: dict[int, dict] = {}
            ordered_regions: dict[int, list] = {}
            for bid, regions in grouped.items():
                regions = sorted(regions, key=lambda r: (r.get("y", 0), r.get("x", 0)))
                uniq, kept = [], []
                for r in regions:
                    txt = r["text"].strip()
                    if txt and (not uniq or uniq[-1] != txt):
                        uniq.append(txt)
                        kept.append(r)
                full = "".join(uniq)
                if not full.strip():
                    continue
                tr_ = m["translator"].translate(full)
                translations[bid] = {"text_zh": tr_["original"], "pinyin": tr_["pinyin"], "vi": tr_["vi"],
                                     "method": tr_["method"], "bubble_id": bid}
                ordered_regions[bid] = kept

            # Stage 4: xoá chữ (hàm của module tự ghi 1 file vào dataset/inpainted -> xoá ngay)
            inp = m["process_and_save"](img=img, text_regions=texts, bubbles=bubbles,
                                       original_filename=f"t{tid}.jpg", text_dilate_px=5, bubble_erode_px=12)
            inpainted = inp["inpainted_img"]
            try:
                if inp.get("saved_path"):
                    Path(inp["saved_path"]).unlink(missing_ok=True)
            except OSError:
                pass

            # Stage 5: đắp chữ Việt
            rendered = m["render_all_bubbles"](img=inpainted, bubbles=bubbles, texts=texts,
                                              bubble_translations=translations, original_img=img)

            inp_file = storage.save_image(db, inpainted, "inpainted", expires_at=expires)
            ren_file = storage.save_image(db, rendered, "rendered", expires_at=expires)

            # Tách từ + map vào từ điển đầy đủ
            all_words = set()
            token_map = {}
            for bid, tr_ in translations.items():
                toks = dictionary.tokenize(tr_["text_zh"])
                token_map[bid] = toks
                all_words.update(tk["w"] for tk in toks)
            ids = dictionary.entry_ids(db, all_words)

            db.query(Bubble).filter(Bubble.translation_id == tid).delete()
            for bid, tr_ in translations.items():
                b = bubbles[bid] if 0 <= bid < len(bubbles) else {}
                regions = ordered_regions[bid]
                lines = [{
                    "text": r["text"].strip(),
                    "x": r.get("x", 0), "y": r.get("y", 0), "w": r.get("w", 0), "h": r.get("h", 0),
                    "polygon": r.get("polygon"),
                    "vertical": bool(r.get("h", 0) > 1.5 * r.get("w", 1) and len(r["text"].strip()) > 1),
                    "confidence": r.get("confidence"),
                    "char_boxes": None,
                } for r in regions]
                if b:
                    bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
                else:  # bubble không còn trong danh sách -> lấy khung bao các dòng
                    bx = int(min(r["x"] for r in regions)); by = int(min(r["y"] for r in regions))
                    bw = int(max(r["x"] + r["w"] for r in regions)) - bx
                    bh = int(max(r["y"] + r["h"] for r in regions)) - by
                style = None
                try:
                    if b:
                        style = _jsonable(m["extract_style"](inpainted, regions, b, original_img=img))
                except Exception:
                    log.debug("extract_style lỗi ở bubble %s", bid, exc_info=True)
                cls = b.get("class_name", "speech_bubble")
                db.add(Bubble(
                    translation_id=tid, idx=bid,
                    class_name=cls if cls in VALID_CLASSES else "speech_bubble",
                    x=int(bx), y=int(by), w=int(bw), h=int(bh),
                    polygon=_jsonable(b.get("polygon")) if b else None,
                    confidence=b.get("confidence"),
                    text_zh=tr_["text_zh"], pinyin=tr_["pinyin"], text_vi=tr_["vi"],
                    translate_method=tr_["method"],
                    lines=_jsonable(lines),
                    tokens=[{**tk, "entry_id": ids.get(tk["w"])} for tk in token_map[bid]],
                    style=style,
                ))

            t.status = "done"
            t.mode = ocr.get("mode")
            t.stats = _jsonable({**ocr.get("stats", {}), "n_inpainted": inp.get("n_regions", 0),
                                 "n_translated": len(translations)})
            t.inpainted_file_id = inp_file.id
            t.rendered_file_id = ren_file.id
            t.processing_ms = int((time.perf_counter() - started) * 1000)
            t.finished_at = datetime.now(timezone.utc)
            db.commit()
            log.info("Translation %s xong: %d bubble, %d ms", tid, len(translations), t.processing_ms)


worker = PipelineWorker()
