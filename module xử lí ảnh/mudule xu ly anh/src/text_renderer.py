"""
src/text_renderer.py — Đắp Chữ Tiếng Việt Vào Bong Bóng (Manhua-grade)
========================================================================
Kiến trúc 4 bước:

  Bước 1 — Style Extraction:
    Trích xuất chiều cao chữ Hán, màu chữ, và mật độ nét (stroke density)
    để chọn font phù hợp (Bold/Italic/Regular) + tính font size khởi điểm.

  Bước 2 — Safe Inner Box:
    Tính vùng viết chữ an toàn (78% x 78% của bbox bubble)
    để chữ không đâm ra ngoài viền cong elip bong bóng.

  Bước 3 — Auto-Fit & Dynamic Bubble Expansion:
    Giảm font size từ ideal xuống min (14px) để chữ vừa safe box.
    Nếu vẫn không vừa → mở rộng polygon bubble 10-25%, tô lại nền + viền.

  Bước 4 — Word-Wrap & Render:
    Ngắt dòng thông minh theo dấu phẩy/chấm/khoảng trắng tiếng Việt.
    Vẽ chữ căn giữa với Pillow, có stroke viền để nổi bật.
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
#  ĐƯỜNG DẪN FONT
# ─────────────────────────────────────────────────────────

_FONT_BASE = Path(r"D:\PTUD\font chữ\Font-chu-truyen-tranh-Comic\Font chữ truyện tranh Comic")

# Font cho từng loại (fallback xuống dưới nếu file không tồn tại)
_FONT_PATHS = {
    # Thoại bình thường
    "dialogue":  _FONT_BASE / "Font-HL-Comic" / "HLcomic1_normal.ttf",
    # Hét to / action
    "action":    _FONT_BASE / "Font-HL-Comic" / "HLcomic3_bold.ttf",
    # Thì thầm / suy nghĩ
    "thought":   _FONT_BASE / "Font-HL-Comic" / "HLcomic8_Italic.ttf",
    # SFX / âm thanh
    "sfx":       _FONT_BASE / "Font TeddyBear" / "000 Mighty Zeo [TeddyBear].ttf",
    # Fallback tuyệt đối
    "fallback":  _FONT_BASE / "Font TeddyBear" / "animeace2_reg.ttf",
}

# Cache font đã load
_font_cache: dict[str, ImageFont.FreeTypeFont] = {}


def _load_font(font_key: str, size: int) -> ImageFont.FreeTypeFont:
    """Load font với cache, tự fallback nếu file không tồn tại."""
    cache_key = f"{font_key}_{size}"
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    path = _FONT_PATHS.get(font_key, _FONT_PATHS["dialogue"])
    if not path.exists():
        path = _FONT_PATHS["fallback"]

    try:
        font = ImageFont.truetype(str(path), size=size)
    except Exception:
        font = ImageFont.load_default()

    _font_cache[cache_key] = font
    return font


# ─────────────────────────────────────────────────────────
#  BƯỚC 1: STYLE EXTRACTION
# ─────────────────────────────────────────────────────────

def extract_style(img: np.ndarray, text_regions: list[dict],
                  bubble: dict, original_img: np.ndarray = None) -> dict:
    """
    Phân tích chữ Hán gốc để lấy màu chữ, cỡ chữ, chọn font.

    QUAN TRỌNG: Truyền original_img (ảnh TRƯỚC inpaint) để extract màu đúng.
    Nếu chỉ truyền img đã inpaint, chữ đã bị xóa → không sample được màu thật.
    """
    # Dùng ảnh gốc để sample màu chữ; fallback về img nếu không có
    src = original_img if original_img is not None else img
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    h_img, w_img = src.shape[:2]

    class_name = bubble.get("class_name", "speech_bubble")

    # --- Kích thước chữ trung bình ---
    # Dùng min(w, h) để lấy đúng kích thước 1 chữ Hán (vì chữ Hán hình vuông)
    # Tránh lỗi lấy nhầm h của cả 1 cột dọc làm chữ bị phóng to khổng lồ
    char_sizes = [min(r.get("w", 0), r.get("h", 0)) for r in text_regions if r.get("w", 0) > 0 and r.get("h", 0) > 0]
    avg_h = float(np.mean(char_sizes)) if char_sizes else 30.0

    # --- Màu lõi chữ ---
    # speech_bubble thường là chữ đen → default an toàn là (20,20,20)
    text_color = (20, 20, 20)

    if original_img is not None and text_regions:
        dark_pixels = []
        for r in text_regions:
            x, y, w, hh = int(r.get("x",0)), int(r.get("y",0)), int(r.get("w",10)), int(r.get("h",10))
            x2, y2 = min(w_img, x+w), min(h_img, y+hh)
            if x2 > x and y2 > y:
                crop_gray = gray[y:y2, x:x2]
                if crop_gray.size > 0 and crop_gray.std() > 15:
                    # Chỉ sample khi vùng có tương phản đủ lớn (có chữ thực sự)
                    thresh = np.percentile(crop_gray, 8)
                    mask = crop_gray < thresh
                    if mask.sum() > 5:
                        crop_bgr = src[y:y2, x:x2]
                        dark_pixels.append(crop_bgr[mask])
        if dark_pixels:
            all_dark = np.vstack(dark_pixels)
            sampled = tuple(int(v) for v in np.median(all_dark, axis=0))
            # Chỉ dùng màu sample nếu nó thực sự là màu tối (< 100 brightness)
            brightness = sum(sampled) / 3
            if brightness < 100:
                text_color = sampled

    # --- Stroke Density ---
    densities = []
    for r in text_regions:
        x, y, w, hh = int(r.get("x",0)), int(r.get("y",0)), int(r.get("w",10)), int(r.get("h",10))
        x2, y2 = min(w_img, x+w), min(h_img, y+hh)
        if x2 > x and y2 > y:
            crop = gray[y:y2, x:x2]
            if crop.std() > 10:
                _, bw = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                density = bw.sum() / 255 / max(bw.size, 1)
                densities.append(density)

    stroke_density = float(np.mean(densities)) if densities else 0.25

    # --- Chọn font key ---
    if class_name == "sound_effect":
        font_key = "sfx"
    elif stroke_density > 0.32 or avg_h > 60:
        font_key = "action"
    elif stroke_density < 0.18:
        font_key = "thought"
    else:
        font_key = "dialogue"

    # --- Font size khởi điểm (Bám sát kích thước chữ Hán gốc) ---
    ideal_font_size = max(16, int(avg_h * 0.9))

    return {
        "avg_char_height":  avg_h,
        "text_color":       text_color,         # BGR
        "stroke_density":   stroke_density,
        "font_key":         font_key,
        "ideal_font_size":  ideal_font_size,
    }


# ─────────────────────────────────────────────────────────
#  BƯỚC 2: SAFE INNER BOX
# ─────────────────────────────────────────────────────────

def get_safe_box(bubble: dict, text_regions: list[dict] = None) -> tuple[int, int, int, int]:
    """
    Tính vùng viết chữ an toàn và tâm của khối chữ.

    Để chữ nằm chính xác giữa bụng bong bóng (tránh bị lệch do đuôi bong bóng),
    ta ưu tiên lấy trọng tâm (center) của các vùng OCR chữ Hán gốc.
    Nếu không có OCR, fallback về trung tâm của YOLO bbox.
    """
    x  = bubble.get("x", 0)
    y  = bubble.get("y", 0)
    bw = bubble.get("w", 100)
    bh = bubble.get("h", 100)

    # Nếu có text_regions, tính tâm dựa trên khung bao của toàn bộ chữ Hán
    if text_regions:
        min_x = min(r.get("x", x) for r in text_regions)
        min_y = min(r.get("y", y) for r in text_regions)
        max_x = max(r.get("x", x) + r.get("w", 0) for r in text_regions)
        max_y = max(r.get("y", y) + r.get("h", 0) for r in text_regions)

        # Tâm của khối chữ Hán gốc
        cx = int((min_x + max_x) / 2)
        cy = int((min_y + max_y) / 2)

        # Fallback an toàn nếu OCR bị out khỏi bubble
        if not (x <= cx <= x + bw): cx = x + bw // 2
        if not (y <= cy <= y + bh): cy = y + bh // 2
    else:
        cx = x + bw // 2
        cy = y + bh // 2

    # 70% theo mỗi chiều (đảm bảo hoàn toàn lọt thỏm trong elip, tránh tràn viền)
    safe_w = int(bw * 0.70)
    safe_h = int(bh * 0.70)

    return cx, cy, safe_w, safe_h


# ─────────────────────────────────────────────────────────
#  BƯỚC 3: WORD-WRAP TIẾNG VIỆT
# ─────────────────────────────────────────────────────────

def smart_wrap(text: str, font: ImageFont.FreeTypeFont,
               max_width: int) -> list[str]:
    """
    Ngắt dòng thông minh cho tiếng Việt:
      - Ưu tiên ngắt sau dấu phẩy (,) để mỗi mệnh đề một dòng
      - Fallback: ngắt theo từ (khoảng trắng)
      - Không bao giờ ngắt giữa chữ

    Returns: list các dòng đã wrap
    """
    # Tách theo dấu phẩy trước để ưu tiên cụm ý nghĩa
    # Ví dụ: "này là câu, sau dấu phẩy xuống hàng" → 2 dòng tự nhiên
    comma_parts = re.split(r'(?<=[,，])\s*', text.strip())

    lines = []
    for part in comma_parts:
        part = part.strip()
        if not part:
            continue
        # Kiểm tra phần này có vừa 1 dòng không
        if _text_width(part, font) <= max_width:
            lines.append(part)
        else:
            # Ngắt theo từ
            words = part.split()
            current = ""
            for word in words:
                candidate = (current + " " + word).strip()
                if _text_width(candidate, font) <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)

    return lines if lines else [text]


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    """Đo chiều rộng chuỗi text với font cho trước."""
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except Exception:
        return len(text) * 10


def _text_height(font: ImageFont.FreeTypeFont) -> int:
    """Chiều cao 1 dòng text."""
    try:
        bbox = font.getbbox("Agy")
        return bbox[3] - bbox[1]
    except Exception:
        return 20


# ─────────────────────────────────────────────────────────
#  BƯỚC 3b: DYNAMIC BUBBLE EXPANSION
# ─────────────────────────────────────────────────────────

def expand_bubble(img: np.ndarray, bubble: dict,
                  bg_color: tuple, scale_x: float, scale_y: float) -> np.ndarray:
    """
    Mở rộng bong bóng:
      1. Kéo giãn polygon từ tâm bubble theo (scale_x, scale_y)
      2. Fill màu nền mới (bg_color) vào vùng mở rộng
      3. Vẽ lại viền đen 2.5px bao quanh

    Returns: ảnh đã vẽ lại bong bóng mở rộng
    """
    result = img.copy()
    h_img, w_img = img.shape[:2]

    x  = bubble.get("x", 0)
    y  = bubble.get("y", 0)
    bw = bubble.get("w", 100)
    bh = bubble.get("h", 100)
    cx = x + bw / 2
    cy = y + bh / 2

    poly = bubble.get("polygon")
    if poly and len(poly) >= 3:
        pts_orig = np.array(poly, dtype=np.float32)
    else:
        # Tạo polygon hình chữ nhật từ bbox
        pts_orig = np.array([
            [x, y], [x+bw, y], [x+bw, y+bh], [x, y+bh]
        ], dtype=np.float32)

    # Kéo giãn từ tâm
    pts_new = np.zeros_like(pts_orig)
    pts_new[:, 0] = cx + (pts_orig[:, 0] - cx) * scale_x
    pts_new[:, 1] = cy + (pts_orig[:, 1] - cy) * scale_y

    # Clamp vào ảnh
    pts_new[:, 0] = np.clip(pts_new[:, 0], 0, w_img - 1)
    pts_new[:, 1] = np.clip(pts_new[:, 1], 0, h_img - 1)
    pts_int = pts_new.astype(np.int32)

    # Fill màu nền
    cv2.fillPoly(result, [pts_int], color=bg_color)

    # Vẽ lại viền đen 2.5px (LINE_AA = anti-alias)
    cv2.polylines(result, [pts_int], isClosed=True,
                  color=(10, 10, 10), thickness=3, lineType=cv2.LINE_AA)

    logger.debug(f"Expand bubble: scale=({scale_x:.2f},{scale_y:.2f})")
    return result


# ─────────────────────────────────────────────────────────
#  BƯỚC 4: RENDER CHỮ TIẾNG VIỆT
# ─────────────────────────────────────────────────────────

def render_text_on_bubble(
    img: np.ndarray,
    bubble: dict,
    vi_text: str,
    text_regions: list[dict],
    bg_color_bgr: tuple = None,
    original_img: np.ndarray = None,
) -> np.ndarray:
    """
    Pipeline đầy đủ 4 bước để đắp chữ tiếng Việt vào 1 bubble.

    Args:
        img:          Ảnh BGR đã inpaint (xóa chữ Hán)
        bubble:       YOLO bubble dict (x,y,w,h,polygon,class_name)
        vi_text:      Bản dịch tiếng Việt
        text_regions: Danh sách text regions OCR của bubble này
        bg_color_bgr: Màu nền bubble (BGR), nếu None sẽ tự sample
        original_img: Ảnh gốc chưa xóa chữ (để extract màu chữ gốc)

    Returns:
        Ảnh BGR đã đắp chữ tiếng Việt
    """
    if not vi_text or not vi_text.strip():
        return img

    # Chuẩn hóa dấu câu: Dịch thuật đôi khi giữ lại dấu câu full-width của tiếng Trung (， 。 ！)
    # Font truyện tranh Việt Nam không hỗ trợ các mã này nên sẽ bị tàng hình.
    # Ta cần quy đổi chúng về dấu câu chuẩn ASCII.
    punctuation_map = {
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "：": ":",
        "；": ";",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "..."
    }
    for k, v in punctuation_map.items():
        vi_text = vi_text.replace(k, v)

    result = img.copy()
    h_img, w_img = img.shape[:2]

    # ── Bước 1: Style Extraction ────────────────────────────────
    style = extract_style(img, text_regions, bubble, original_img)
    font_key        = style["font_key"]
    ideal_font_size = style["ideal_font_size"]
    text_color_bgr  = style["text_color"]

    # Chuyển màu chữ sang RGB cho Pillow
    text_color_rgb = (text_color_bgr[2], text_color_bgr[1], text_color_bgr[0])

    # Màu viền chữ (stroke): đối nghịch với màu nền
    # Nếu chữ tối → viền sáng; nếu chữ sáng → viền tối
    avg_brightness = sum(text_color_rgb) / 3
    if avg_brightness < 128:
        stroke_color = (255, 255, 255)   # stroke trắng
        stroke_w = 2
    else:
        stroke_color = (0, 0, 0)         # stroke đen
        stroke_w = 2

    # ── Bước 2: Safe Inner Box ──────────────────────────────────
    cx, cy, safe_w, safe_h = get_safe_box(bubble, text_regions)

    # ── Sample màu nền bubble ───────────────────────────────────
    if bg_color_bgr is None:
        x  = bubble.get("x", 0)
        y  = bubble.get("y", 0)
        bw = bubble.get("w", 100)
        bh = bubble.get("h", 100)
        # Lấy mẫu ở vùng trung tâm bubble (sau inpaint đã sạch)
        pad = max(10, bw // 8)
        rx1, ry1 = max(0, cx - pad), max(0, cy - pad)
        rx2, ry2 = min(w_img, cx + pad), min(h_img, cy + pad)
        center_patch = result[ry1:ry2, rx1:rx2]
        if center_patch.size > 0:
            bg_color_bgr = tuple(int(v) for v in np.median(
                center_patch.reshape(-1, 3), axis=0
            ))
        else:
            bg_color_bgr = (255, 255, 255)

    bg_color_rgb = (bg_color_bgr[2], bg_color_bgr[1], bg_color_bgr[0])

    # ── Bước 3: Auto-fit font size ──────────────────────────────
    MIN_FONT = 13
    # Bắt đầu đúng bằng cỡ chữ lý tưởng (đã tính theo chữ Hán gốc)
    # Không dùng số 100 nữa để tránh bị phóng to lố lăng
    font_size = ideal_font_size
    lines = []
    total_h = 0
    LINE_SPACING = 1.45   # Giãn cách dòng thoáng hơn

    while font_size >= MIN_FONT:
        font = _load_font(font_key, font_size)
        lines = smart_wrap(vi_text, font, safe_w)
        line_h = _text_height(font)
        total_h = int(len(lines) * line_h * LINE_SPACING)
        
        # Phải kiểm tra cả bề ngang, vì smart_wrap có thể giữ 1 từ rất dài trên 1 dòng
        max_line_w = max([_text_width(l, font) for l in lines] + [0])
        
        if total_h <= safe_h and max_line_w <= safe_w:
            break
        font_size -= 1

    # Nếu vẫn không vừa → kích hoạt Dynamic Bubble Expansion
    if font_size < MIN_FONT or total_h > safe_h or max_line_w > safe_w:
        font_size = max(font_size, MIN_FONT)
        font = _load_font(font_key, font_size)
        lines = smart_wrap(vi_text, font, safe_w)
        line_h = _text_height(font)
        total_h = int(len(lines) * line_h * LINE_SPACING)
        max_line_w = max([_text_width(l, font) for l in lines] + [0])

        if total_h > safe_h or max_line_w > safe_w:
            scale_factor_y = min(1.25, total_h / safe_h * 1.05) if total_h > safe_h else 1.0
            scale_factor_x = min(1.25, max_line_w / safe_w * 1.05) if max_line_w > safe_w else 1.0
            
            scale_x = scale_factor_x
            scale_y = scale_factor_y

            result = expand_bubble(result, bubble, bg_color_bgr, scale_x, scale_y)

            # Cập nhật safe_h sau khi mở rộng
            safe_h = int(safe_h * scale_y)
            safe_w = int(safe_w * scale_x)
            logger.info(f"Bubble expanded: sx={scale_x:.2f} sy={scale_y:.2f}")

    # ── Bước 4: Render chữ với Pillow ───────────────────────────
    # Chuyển ảnh OpenCV (BGR) → Pillow (RGB)
    pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    font = _load_font(font_key, font_size)
    line_h = _text_height(font)
    line_spacing_px = int(line_h * LINE_SPACING)

    # Tính vị trí Y bắt đầu (căn giữa dọc khối chữ)
    block_h = len(lines) * line_spacing_px
    y_start = cy - block_h // 2 + line_spacing_px // 2

    for i, line in enumerate(lines):
        ly = y_start + i * line_spacing_px

        # Pillow tự động căn giữa ngang và dọc với anchor="mm"
        # Hỗ trợ native viền chữ (stroke_width) chống mờ nhòe
        draw.text(
            (cx, ly),
            line,
            font=font,
            fill=text_color_rgb,
            anchor="mm",
            stroke_width=stroke_w,
            stroke_fill=stroke_color
        )

    # Chuyển lại sang OpenCV BGR
    result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return result


# ─────────────────────────────────────────────────────────
#  HÀM CHÍNH: XỬ LÝ TOÀN BỘ TRANG
# ─────────────────────────────────────────────────────────

def render_all_bubbles(
    img: np.ndarray,
    bubbles: list[dict],
    texts: list[dict],
    bubble_translations: dict,
    original_img: np.ndarray = None,
) -> np.ndarray:
    """
    Đắp chữ tiếng Việt vào TẤT CẢ bong bóng trong ảnh.

    Args:
        img:                  Ảnh đã inpaint (xóa chữ Hán)
        bubbles:              List bubble từ YOLO (theo thứ tự index)
        texts:                Tất cả text_regions đã OCR
        bubble_translations:  Dict {bubble_id → {vi, text_zh, pinyin}}
        original_img:         Ảnh gốc (để extract màu chữ, chưa xóa chữ Hán)

    Returns:
        Ảnh BGR đã đắp chữ tiếng Việt vào tất cả bubble
    """
    result = img.copy()

    # Nhóm text_regions theo bubble_id
    texts_by_bubble: dict[int, list] = {}
    for t in texts:
        bid = t.get("bubble_id", -1)
        if bid >= 0:
            if bid not in texts_by_bubble:
                texts_by_bubble[bid] = []
            texts_by_bubble[bid].append(t)

    for bubble_id, bt in bubble_translations.items():
        vi_text = bt.get("vi", "").strip()
        if not vi_text:
            continue

        if bubble_id >= len(bubbles):
            continue

        bubble = bubbles[bubble_id]
        regions = texts_by_bubble.get(bubble_id, [])

        try:
            result = render_text_on_bubble(
                img=result,
                bubble=bubble,
                vi_text=vi_text,
                text_regions=regions,
                bg_color_bgr=None,
                original_img=original_img,
            )
            logger.info(f"Render bubble {bubble_id}: '{vi_text[:30]}...'")
        except Exception as e:
            logger.error(f"Lỗi render bubble {bubble_id}: {e}", exc_info=True)

    return result
