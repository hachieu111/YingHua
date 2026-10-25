"""Hàm thuần dựng kết quả bong bóng từ đầu ra OCR (gom dòng, khử trùng, khung bao, chuẩn hóa lớp).

Giữ đúng logic của `Backend/app/services/pipeline_runner.py` bản cũ; chỉ tách thành hàm nhỏ để test được.
"""

from __future__ import annotations

import json
from typing import Any

VALID_CLASSES = frozenset({"speech_bubble", "sound_effect", "calligraphy", "floating_text"})
DEFAULT_CLASS = "speech_bubble"
# Dòng cao hơn 1.5 lần bề rộng (và dài hơn 1 chữ) coi là chữ dọc.
VERTICAL_ASPECT_RATIO = 1.5

Region = dict[str, Any]


def _to_plain(o: Any) -> Any:
    # Mảng nhiều phần tử phải `tolist()` trước: `item()` chỉ chạy với mảng 1 phần tử (bản cũ gọi item trước).
    if getattr(o, "ndim", 0) > 0 and hasattr(o, "tolist"):
        return o.tolist()
    if hasattr(o, "item"):
        return o.item()
    if hasattr(o, "tolist"):
        return o.tolist()
    return str(o)


def jsonable(obj: Any) -> Any:
    """Đổi numpy/tuple về kiểu JSON thuần (style, polygon, stats có thể chứa numpy)."""
    return json.loads(json.dumps(obj, default=_to_plain))


def select_bubble_texts(texts: list[Region]) -> list[Region]:
    """Chỉ giữ dòng thuộc một bong bóng (`bubble_id >= 0`)."""
    return [t for t in texts if t.get("bubble_id", -1) >= 0]


def group_by_bubble(texts: list[Region]) -> dict[int, list[Region]]:
    """Gom dòng theo `bubble_id`, giữ thứ tự xuất hiện của bong bóng."""
    grouped: dict[int, list[Region]] = {}
    for t in texts:
        grouped.setdefault(t["bubble_id"], []).append(t)
    return grouped


def order_and_dedupe(regions: list[Region]) -> tuple[list[str], list[Region]]:
    """Sắp dòng theo (y, x) rồi bỏ dòng rỗng và dòng trùng liền kề (OCR hay đọc lặp)."""
    ordered = sorted(regions, key=lambda r: (r.get("y", 0), r.get("x", 0)))
    texts: list[str] = []
    kept: list[Region] = []
    for r in ordered:
        txt = r["text"].strip()
        if txt and (not texts or texts[-1] != txt):
            texts.append(txt)
            kept.append(r)
    return texts, kept


def normalize_class_name(name: Any) -> str:
    """Đưa lớp YOLO về 1 trong 4 lớp hợp lệ; lạ hoặc thiếu → `speech_bubble`."""
    return name if name in VALID_CLASSES else DEFAULT_CLASS


def is_vertical(region: Region) -> bool:
    """Dòng chữ dọc: cao > 1.5 × rộng và có hơn 1 ký tự."""
    return bool(
        region.get("h", 0) > VERTICAL_ASPECT_RATIO * region.get("w", 1) and len(region["text"].strip()) > 1
    )


def build_lines(regions: list[Region]) -> list[dict[str, Any]]:
    """Dòng OCR của một bong bóng ở dạng lưu trữ (JSON thuần)."""
    lines = [
        {
            "text": r["text"].strip(),
            "x": r.get("x", 0),
            "y": r.get("y", 0),
            "w": r.get("w", 0),
            "h": r.get("h", 0),
            "polygon": r.get("polygon"),
            "vertical": is_vertical(r),
            "confidence": r.get("confidence"),
            "char_boxes": None,
        }
        for r in regions
    ]
    result: list[dict[str, Any]] = jsonable(lines)
    return result


def bounding_box(regions: list[Region]) -> tuple[int, int, int, int]:
    """Khung bao (x, y, w, h) của các dòng — dùng khi bong bóng không còn trong danh sách YOLO."""
    x = int(min(r["x"] for r in regions))
    y = int(min(r["y"] for r in regions))
    w = int(max(r["x"] + r["w"] for r in regions)) - x
    h = int(max(r["y"] + r["h"] for r in regions)) - y
    return x, y, w, h


def bubble_box(bubble: Region, regions: list[Region]) -> tuple[int, int, int, int]:
    """Khung của bong bóng YOLO, hoặc khung bao các dòng nếu không có bong bóng."""
    if bubble:
        return int(bubble["x"]), int(bubble["y"]), int(bubble["w"]), int(bubble["h"])
    return bounding_box(regions)


def find_bubble(bubbles: list[Region], bubble_id: int) -> Region:
    """Bong bóng theo chỉ số; ngoài phạm vi → `{}` (giống bản cũ)."""
    return bubbles[bubble_id] if 0 <= bubble_id < len(bubbles) else {}
