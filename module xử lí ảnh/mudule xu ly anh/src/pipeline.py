"""
Module: pipeline.py
Mục tiêu: Core ML Pipeline kết hợp YOLOv8 Segmentation (Multi-class) + PP-OCRv4 (OCR)
          Hỗ trợ đầy đủ 3 class: speech_bubble | sound_effect | calligraphy
          + Logic dự phòng phát hiện Floating Text tự động

Pipeline Flow:
  Ảnh gốc
    → YOLOv8 (Phát hiện bubble theo class: speech_bubble / sound_effect / calligraphy)
    → PP-OCRv4 (Đọc chữ trong từng vùng)
    → Floating Text Detection (Chữ nào KHÔNG trong bubble nào → floating_text)
    → JSON {text, box, class, bubble_id}
"""

import cv2
import numpy as np
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


# ===================== CLASS DEFINITIONS =====================
CLASS_NAMES = ["speech_bubble", "sound_effect", "calligraphy"]
CLASS_LABELS = {
    "speech_bubble": "💬 Bong bóng chat",
    "sound_effect":  "💥 Âm thanh / SFX",
    "calligraphy":   "✍️ Thư pháp / Chiêu thức",
    "floating_text": "🌊 Chữ trôi nổi (Auto-detected)",
}


def _iou(ax: float, ay: float, aw: float, ah: float,
         bx: float, by: float, bw: float, bh: float) -> float:
    """Tính Intersection-over-Union giữa 2 bbox."""
    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax + aw, bx + bw)
    iy2 = min(ay + ah, by + bh)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _overlap_ratio(fx: float, fy: float, fw: float, fh: float,
                   bx: float, by: float, bw: float, bh: float) -> float:
    """
    Tỉ lệ phần vùng nhỏ (floating) bị bao phủ bởi vùng lớn (bubble).
    Dùng thay IoU vì bubble thường lớn hơn nhiều so với text region.
    """
    ix1 = max(fx, bx)
    iy1 = max(fy, by)
    ix2 = min(fx + fw, bx + bw)
    iy2 = min(fy + fh, by + bh)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    float_area = fw * fh
    return inter / float_area if float_area > 0 else 0.0


class ComicOCRPipeline:
    """
    Pipeline đa lớp để bóc tách và phân loại text trong truyện tranh.

    Stage 1: YOLOv8 phát hiện vùng text theo class (speech_bubble / sound_effect / calligraphy)
    Stage 2: PP-OCRv4 đọc chữ trong từng vùng được detect
    Stage 3: Floating Text Detection — chạy PP-OCR trên toàn ảnh, lọc ra vùng
             nào không thuộc bất kỳ YOLO bubble nào (overlap < threshold)
    """

    def __init__(
        self,
        yolo_model_path: str = None,
        ocr_lang: str = "ch",
        yolo_conf_threshold: float = 0.30,
        ocr_conf_threshold: float = 0.45,
        floating_overlap_threshold: float = 0.30,
        use_gpu: bool = False
    ):
        """
        Args:
            yolo_model_path:            Đường dẫn tới model YOLOv8 đã train (.pt).
                                        Nếu None → dùng PP-OCR thuần (fallback mode).
            ocr_lang:                   Ngôn ngữ OCR ('ch' = Tiếng Trung).
            yolo_conf_threshold:        Ngưỡng confidence cho bubble detection.
            ocr_conf_threshold:         Ngưỡng confidence để lọc text OCR.
            floating_overlap_threshold: Ngưỡng overlap để xác định floating text.
                                        Nếu text region bị bao phủ < threshold → floating.
            use_gpu:                    True nếu có GPU (CUDA).
        """
        self.yolo_conf              = yolo_conf_threshold
        self.ocr_conf               = ocr_conf_threshold
        self.floating_threshold     = floating_overlap_threshold
        self.yolo_available         = False

        # === Khởi tạo YOLOv8 ===
        if yolo_model_path and Path(yolo_model_path).exists():
            try:
                from ultralytics import YOLO
                self.yolo = YOLO(yolo_model_path)
                self.yolo_available = True
                logger.info(f"✅ YOLOv8 loaded: {yolo_model_path}")
            except ImportError:
                logger.warning("⚠️  ultralytics chưa cài. Dùng fallback PP-OCR thuần.")
            except Exception as e:
                logger.error(f"❌ Lỗi load YOLO: {e}. Dùng fallback mode.")
        else:
            logger.info("ℹ️  Không có YOLO model → Chạy PP-OCR trực tiếp trên toàn ảnh (fallback mode)")

        # === Khởi tạo PP-OCRv4 ===
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=ocr_lang,
                use_gpu=use_gpu,
                show_log=False,
                det_model_dir=None,  # Auto-download model tốt nhất
                rec_model_dir=None,
            )
            logger.info("✅ PP-OCR loaded thành công")
        except ImportError:
            raise ImportError("paddleocr chưa được cài đặt! Chạy: pip install paddleocr")

    # ------------------------------------------------------------------ #
    #  STAGE 1: DETECT BUBBLES (YOLO multi-class)                         #
    # ------------------------------------------------------------------ #
    def detect_bubbles(self, img: np.ndarray) -> list[dict]:
        """
        Stage 1: Phát hiện vùng text bằng YOLOv8 (multi-class).

        Returns:
            List of dicts:
            {
                "x", "y", "w", "h": tọa độ bbox tuyệt đối,
                "class_id":  int (0=speech_bubble, 1=sound_effect, 2=calligraphy),
                "class_name": str,
                "confidence": float,
                "polygon":   [[x,y], ...] nếu model là segmentation, else None
            }
        """
        if not self.yolo_available:
            # Fallback: toàn ảnh = 1 vùng speech_bubble
            h, w = img.shape[:2]
            return [{
                "x": 0, "y": 0, "w": w, "h": h,
                "class_id": 0, "class_name": "speech_bubble",
                "confidence": 1.0, "polygon": None
            }]

        # Chạy YOLO (hỗ trợ cả detection và segmentation)
        results = self.yolo.predict(
            img,
            conf=self.yolo_conf,
            verbose=False,
            imgsz=1280
        )

        bubbles = []
        for r in results:
            # ---- Polygon (segmentation model) ----
            masks = getattr(r, "masks", None)
            for i, box in enumerate(r.boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf     = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = (CLASS_NAMES[class_id]
                              if class_id < len(CLASS_NAMES)
                              else f"class_{class_id}")

                # Lấy polygon nếu là segmentation model
                polygon = None
                if masks is not None and i < len(masks):
                    try:
                        # masks.xy[i] → [[x,y], ...]
                        poly = masks.xy[i].tolist()
                        polygon = [[float(p[0]), float(p[1])] for p in poly]
                    except Exception:
                        polygon = None

                bubbles.append({
                    "x": int(x1),
                    "y": int(y1),
                    "w": int(x2 - x1),
                    "h": int(y2 - y1),
                    "class_id":   class_id,
                    "class_name": class_name,
                    "confidence": round(conf, 4),
                    "polygon":    polygon,
                })

        # Thuật toán MERGE: Gộp các bong bóng chạm/đè nhau thành 1 bong bóng to duy nhất.
        # Giải quyết lỗi: YOLO cắt 1 bong bóng thành 2-3 bong bóng nhỏ (trái/phải),
        # làm mất chữ hoặc làm chữ dịch ra bị chia lẻ.
        merged_bubbles = []
        # Ưu tiên bong bóng to xử lý trước
        bubbles.sort(key=lambda b: b["w"] * b["h"], reverse=True)
        
        for b in bubbles:
            merged = False
            for mb in merged_bubbles:
                # Mở rộng nhẹ vùng check (padding 15px) để các bong bóng cách nhau dưới 30px cũng bị gộp
                pad = 15
                x_left = max(b["x"] - pad, mb["x"] - pad)
                y_top = max(b["y"] - pad, mb["y"] - pad)
                x_right = min(b["x"] + b["w"] + pad, mb["x"] + mb["w"] + pad)
                y_bottom = min(b["y"] + b["h"] + pad, mb["y"] + mb["h"] + pad)

                if b["class_id"] == mb["class_id"] and x_right > x_left and y_bottom > y_top:
                    # Gộp b vào mb (Cập nhật bbox to nhất bao trọn cả hai)
                    new_x = min(mb["x"], b["x"])
                    new_y = min(mb["y"], b["y"])
                    new_w = max(mb["x"] + mb["w"], b["x"] + b["w"]) - new_x
                    new_h = max(mb["y"] + mb["h"], b["y"] + b["h"]) - new_y
                    
                    mb["x"], mb["y"], mb["w"], mb["h"] = new_x, new_y, new_w, new_h
                    
                    # Cập nhật polygon bằng thuật toán Convex Hull (bao lồi)
                    # Giúp bọc trọn 2 polygon thành 1 khối mượt mà, không bị cắt chéo
                    if mb.get("polygon") and b.get("polygon"):
                        import numpy as np
                        import cv2
                        combined_pts = np.array(mb["polygon"] + b["polygon"], dtype=np.float32)
                        hull = cv2.convexHull(combined_pts)
                        mb["polygon"] = hull[:, 0, :].tolist()
                    elif b.get("polygon"):
                        mb["polygon"] = b["polygon"]
                        
                    merged = True
                    break
            
            if not merged:
                merged_bubbles.append(b)

        logger.debug(f"YOLO phát hiện {len(merged_bubbles)} vùng text (đã gộp các vùng sát nhau)")
        return merged_bubbles

    # ------------------------------------------------------------------ #
    #  STAGE 2: OCR TỪNG BUBBLE                                           #
    # ------------------------------------------------------------------ #
    def ocr_bubble(self, img: np.ndarray, bubble: dict) -> list[dict]:
        """
        Stage 2: OCR trên vùng ảnh được crop từ bubble.

        Returns:
            List of {
                "text", "x", "y", "w", "h", "confidence",
                "class_id", "class_name", "polygon", "source"
            }
            Tọa độ đã được convert về không gian ảnh GỐC.
        """
        bx, by, bw, bh = bubble["x"], bubble["y"], bubble["w"], bubble["h"]
        img_h, img_w   = img.shape[:2]

        x1 = max(0, bx)
        y1 = max(0, by)
        x2 = min(img_w, bx + bw)
        y2 = min(img_h, by + bh)
        crop = img[y1:y2, x1:x2]

        if crop.size == 0:
            return []

        try:
            result = self.ocr.ocr(crop, cls=True)
        except Exception as e:
            logger.error(f"OCR lỗi: {e}")
            return []

        if not result or not result[0]:
            return []

        texts = []
        for line in result[0]:
            poly_points = line[0]
            text        = line[1][0]
            confidence  = float(line[1][1])

            if confidence < self.ocr_conf:
                continue

            xs = [pt[0] for pt in poly_points]
            ys = [pt[1] for pt in poly_points]

            # Convert local → absolute
            abs_x = min(xs) + x1
            abs_y = min(ys) + y1
            abs_w = max(xs) - min(xs)
            abs_h = max(ys) - min(ys)

            texts.append({
                "text":       text,
                "x":          round(abs_x, 2),
                "y":          round(abs_y, 2),
                "w":          round(abs_w, 2),
                "h":          round(abs_h, 2),
                "confidence": round(confidence, 4),
                "class_id":   bubble.get("class_id", 0),
                "class_name": bubble.get("class_name", "speech_bubble"),
                "source":     "bubble_ocr",
                "polygon": [
                    [round(pt[0] + x1, 2), round(pt[1] + y1, 2)]
                    for pt in poly_points
                ],
            })

        return texts

    # ------------------------------------------------------------------ #
    #  STAGE 3: FLOATING TEXT DETECTION (Logic Dự Phòng)                  #
    # ------------------------------------------------------------------ #
    def detect_floating_text(
        self,
        img: np.ndarray,
        bubbles: list[dict]
    ) -> list[dict]:
        """
        Stage 3: Phát hiện Floating Text — chữ nằm NGOÀI bong bóng.

        Thuật toán:
          1. Chạy PP-OCR trên toàn ảnh gốc (không crop).
          2. Với mỗi vùng text tìm được:
             - Tính overlap với TẤT CẢ bubble YOLO đã phát hiện.
             - Nếu overlap_ratio < floating_threshold → đây là floating text.
          3. Trả về list floating text regions.

        Args:
            img:     Ảnh BGR gốc.
            bubbles: Danh sách bubble từ YOLO (Stage 1).

        Returns:
            List of text dicts với class_name = "floating_text".
        """
        logger.info("Stage 3: Chạy Floating Text Detection trên toàn ảnh...")

        try:
            result = self.ocr.ocr(img, cls=True)
        except Exception as e:
            logger.error(f"OCR toàn ảnh lỗi: {e}")
            return []

        if not result or not result[0]:
            return []

        floating = []
        total_ocr = len(result[0])

        for line in result[0]:
            poly_points = line[0]
            text        = line[1][0]
            confidence  = float(line[1][1])

            if confidence < self.ocr_conf:
                continue

            xs = [pt[0] for pt in poly_points]
            ys = [pt[1] for pt in poly_points]
            fx, fy = min(xs), min(ys)
            fw, fh = max(xs) - fx, max(ys) - fy

            # Tính overlap với từng bubble
            max_overlap = 0.0
            for bubble in bubbles:
                bx, by, bw, bh = bubble["x"], bubble["y"], bubble["w"], bubble["h"]
                overlap = _overlap_ratio(fx, fy, fw, fh, bx, by, bw, bh)
                if overlap > max_overlap:
                    max_overlap = overlap

            if max_overlap < self.floating_threshold:
                # Đây là floating text — không thuộc bubble nào
                floating.append({
                    "text":       text,
                    "x":          round(fx, 2),
                    "y":          round(fy, 2),
                    "w":          round(fw, 2),
                    "h":          round(fh, 2),
                    "confidence": round(confidence, 4),
                    "class_id":   3,               # floating_text = class 3
                    "class_name": "floating_text",
                    "source":     "floating_fallback",
                    "overlap":    round(max_overlap, 3),
                    "polygon": [
                        [round(pt[0], 2), round(pt[1], 2)]
                        for pt in poly_points
                    ],
                })

        logger.info(
            f"Stage 3 xong: {len(floating)}/{total_ocr} vùng text là floating "
            f"(threshold overlap < {self.floating_threshold})"
        )
        return floating

    # ------------------------------------------------------------------ #
    #  MAIN PROCESS                                                        #
    # ------------------------------------------------------------------ #
    def process(self, image_input, detect_floating: bool = True) -> dict:
        """
        Hàm chính: Xử lý toàn bộ pipeline cho 1 ảnh.

        Args:
            image_input:    Đường dẫn file (str/Path) HOẶC numpy array BGR.
            detect_floating: True để chạy Stage 3 (Floating Text Detection).

        Returns:
            {
                "width": int,
                "height": int,
                "mode": str,
                "bubbles": [           # YOLO bubbles (multi-class)
                    {
                        "x","y","w","h",
                        "class_id","class_name","confidence","polygon"
                    }
                ],
                "texts": [             # TẤT CẢ text (bubble OCR + floating)
                    {
                        "text","x","y","w","h","confidence",
                        "class_id","class_name","source","bubble_id","polygon"
                    }
                ],
                "floating_texts": [    # Chỉ floating text (subset của texts)
                    {...}
                ],
                "stats": {
                    "speech_bubble": int,
                    "sound_effect": int,
                    "calligraphy": int,
                    "floating_text": int,
                    "total": int
                }
            }
        """
        # Load ảnh
        if isinstance(image_input, (str, Path)):
            img = cv2.imdecode(
                np.fromfile(str(image_input), dtype=np.uint8),
                cv2.IMREAD_COLOR
            )
            if img is None:
                raise FileNotFoundError(f"Không đọc được ảnh: {image_input}")
        else:
            img = image_input

        img_h, img_w = img.shape[:2]
        logger.info(f"Đang xử lý ảnh {img_w}x{img_h}...")

        # ---- Stage 1: Detect bubbles (multi-class) ----
        bubbles = self.detect_bubbles(img)
        logger.info(
            f"Stage 1 xong: {len(bubbles)} vùng — "
            + ", ".join(
                f"{b['class_name']}" for b in bubbles[:5]
            ) + ("..." if len(bubbles) > 5 else "")
        )

        # ---- Stage 2: OCR từng bubble ----
        all_texts = []
        for bubble_id, bubble in enumerate(bubbles):
            texts_in_bubble = self.ocr_bubble(img, bubble)
            for t in texts_in_bubble:
                t["bubble_id"] = bubble_id
            all_texts.extend(texts_in_bubble)
        logger.info(f"Stage 2 xong: {len(all_texts)} text regions từ bubbles")

        # ---- Stage 3: Floating Text Detection ----
        floating_texts = []
        if detect_floating and self.yolo_available:
            # Chỉ chạy khi có YOLO (nếu không có YOLO thì toàn bộ đã là "fallback")
            floating_texts = self.detect_floating_text(img, bubbles)
            for ft in floating_texts:
                ft["bubble_id"] = -1  # -1 = không thuộc bubble nào
            all_texts.extend(floating_texts)
        elif detect_floating and not self.yolo_available:
            logger.info("Bỏ qua Floating Text Detection (chưa có YOLO model)")

        # ---- Thống kê ----
        stats = {name: 0 for name in CLASS_NAMES}
        stats["floating_text"] = 0
        for t in all_texts:
            name = t.get("class_name", "speech_bubble")
            if name in stats:
                stats[name] += 1
        stats["total"] = len(all_texts)

        mode = "yolo_segmentation+ocr" if self.yolo_available else "ocr_only_fallback"

        return {
            "width":          img_w,
            "height":         img_h,
            "mode":           mode,
            "bubbles":        bubbles,
            "texts":          all_texts,
            "floating_texts": floating_texts,
            "stats":          stats,
        }


# ==================== Singleton Pattern ====================
_pipeline_instance: ComicOCRPipeline | None = None

YOLO_MODEL_PATH = r"d:\PTUD\mudule xu ly anh\models bong bóng\model.pt"


def get_pipeline() -> ComicOCRPipeline:
    """
    Lấy singleton instance của pipeline.
    Tự động dùng YOLO nếu model đã được train,
    fallback về PP-OCR thuần nếu chưa có model YOLO.
    """
    global _pipeline_instance

    if _pipeline_instance is None:
        yolo_path = YOLO_MODEL_PATH if Path(YOLO_MODEL_PATH).exists() else None

        if yolo_path:
            logger.info(f"Khởi tạo Pipeline: YOLO Segmentation + PP-OCR (model: {yolo_path})")
        else:
            logger.info("Khởi tạo Pipeline: PP-OCR Fallback Mode (chưa có YOLO model)")

        _pipeline_instance = ComicOCRPipeline(
            yolo_model_path=yolo_path,
            yolo_conf_threshold=0.30,
            ocr_conf_threshold=0.45,
            floating_overlap_threshold=0.30,
        )

    return _pipeline_instance
