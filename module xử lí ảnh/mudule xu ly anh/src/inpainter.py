"""
src/inpainter.py — Module Xóa Chữ Chuẩn (Manhua-grade)
========================================================
Kỹ thuật: Dilate Text Mask + Erode Bubble Fence + Median Fill

  Bước 1 — Tạo Text Mask chính xác (per bubble):
    - Lấy polygon của từng text region (PP-OCR) trong bubble
    - Thresholding vùng chữ để bắt đúng nét (không bỏ sót)
    - Dilate mask 5px để "nuốt" toàn bộ viền mờ / nhiễu JPEG

  Bước 2 — Co Bubble Mask làm hàng rào:
    - Lấy bbox / polygon của bubble từ YOLO
    - Erode vào trong 5px → tạo "safe zone" để tránh ăn vào viền bubble

  Bước 3 — Median Color Fill:
    - Background pixels = vùng trong safe_zone NGOÀI text_mask
    - Median màu từ toàn bộ background pixels đó
    - Fill text_mask bằng màu median → đồng nhất tuyệt đối, không gợn

  Kết quả: Hoạt động đúng với MỌI màu nền (trắng, màu, gradient)
           Không phụ thuộc vào TELEA / AI / GPU
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).parent.parent
INPAINT_DIR = BASE_DIR / "dataset" / "inpainted"
INPAINT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────
#  BƯỚC 1: TẠO TEXT MASK CHÍNH XÁC
# ─────────────────────────────────────────────────────────────────

def _make_text_mask(img: np.ndarray, text_regions: list[dict],
                   dilate_px: int = 5) -> np.ndarray:
    """
    Tạo mask che vùng chữ với độ chính xác cao:

    - Polygon từ PP-OCR → fill vùng bounding box chữ
    - Thresholding Otsu bên trong bbox để bắt các nét pixel tối
    - Dilate 5px để ăn hết viền mờ / anti-alias / nhiễu JPEG

    Returns: mask uint8 [H,W] với 255=vùng cần xóa, 0=giữ nguyên
    """
    h, w = img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    for region in text_regions:
        poly = region.get("polygon")

        if poly and len(poly) >= 3:
            pts = np.array(poly, dtype=np.int32)
            x, y, rw, rh = cv2.boundingRect(pts)
        else:
            x  = int(region.get("x", 0))
            y  = int(region.get("y", 0))
            rw = int(region.get("w", 0))
            rh = int(region.get("h", 0))
            if rw <= 0 or rh <= 0:
                continue
            pts = np.array([[x, y], [x+rw, y], [x+rw, y+rh], [x, y+rh]], np.int32)

        # Clamp bbox vào ảnh
        x1 = max(0, x - 2)
        y1 = max(0, y - 2)
        x2 = min(w, x + rw + 2)
        y2 = min(h, y + rh + 2)
        if x2 <= x1 or y2 <= y1:
            continue

        crop = gray[y1:y2, x1:x2]

        # Thresholding Otsu trong crop → bắt pixel chữ (tối hơn nền)
        # Nếu crop quá nhỏ hoặc phẳng, dùng threshold cứng
        if crop.std() > 8:
            _, thresh = cv2.threshold(crop, 0, 255,
                                      cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            # Nền trắng: chữ là pixel tối
            _, thresh = cv2.threshold(crop, 200, 255, cv2.THRESH_BINARY_INV)

        # Đặt thresh vào mask toàn ảnh
        sub_mask = np.zeros((h, w), dtype=np.uint8)
        sub_mask[y1:y2, x1:x2] = thresh

        # Giới hạn trong polygon OCR (không lan sang vùng ngoài)
        poly_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(poly_mask, [pts], 255)
        sub_mask = cv2.bitwise_and(sub_mask, poly_mask)

        mask = cv2.bitwise_or(mask, sub_mask)

    # Dilate: ăn hết viền chữ + nhiễu xung quanh
    if dilate_px > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (dilate_px * 2 + 1, dilate_px * 2 + 1)
        )
        mask = cv2.dilate(mask, kernel)

    # Morph close: lấp lỗ hổng nhỏ giữa các nét chữ (chữ có nét đứt)
    close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k)

    return mask


# ─────────────────────────────────────────────────────────────────
#  BƯỚC 2: TẠO SAFE ZONE TỪ BUBBLE POLYGON (ERODE)
# ─────────────────────────────────────────────────────────────────

def _make_bubble_safe_zone(img_h: int, img_w: int,
                            bubble: dict, erode_px: int = 5) -> np.ndarray:
    """
    Tạo safe zone = vùng bên trong bubble đã co vào erode_px pixel.

    Mục đích: Ngăn text_mask lan vào viền đen của bubble.
    Nếu không có polygon YOLO, dùng bbox.

    Returns: mask uint8 [H,W] với 255=vùng an toàn để xóa
    """
    safe = np.zeros((img_h, img_w), dtype=np.uint8)

    poly = bubble.get("polygon")
    if poly and len(poly) >= 3:
        pts = np.array(poly, dtype=np.int32)
        cv2.fillPoly(safe, [pts], 255)
    else:
        x  = bubble.get("x", 0)
        y  = bubble.get("y", 0)
        bw = bubble.get("w", 0)
        bh = bubble.get("h", 0)
        if bw > 0 and bh > 0:
            cv2.rectangle(safe, (x, y), (x + bw, y + bh), 255, -1)
        else:
            # Không có thông tin bubble → safe zone = toàn ảnh
            safe[:] = 255
            return safe

    # Erode vào trong để tạo hàng rào
    if erode_px > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (erode_px * 2 + 1, erode_px * 2 + 1)
        )
        safe = cv2.erode(safe, kernel)

    return safe


# ─────────────────────────────────────────────────────────────────
#  BƯỚC 3: MEDIAN COLOR FILL
# ─────────────────────────────────────────────────────────────────

def _median_fill(img: np.ndarray, result: np.ndarray,
                 erase_mask: np.ndarray, safe_zone: np.ndarray,
                 text_mask_before_dilate: np.ndarray = None) -> None:
    """
    Fill vùng erase_mask bằng màu median của background pixels.

    Background pixels = pixel bên trong safe_zone NHƯNG NGOÀI text_mask.

    Tại sao median tốt hơn mean?
      Mean bị kéo bởi các pixel outlier (viền tối, chữ sót).
      Median luôn là màu "đại diện" nhất của nền → fill đồng nhất.

    Modifies `result` in-place.
    """
    # Background = safe zone AND NOT erase_mask
    # (lấy pixel nền thực sự, không bị ô nhiễm bởi chữ)
    bg_mask = cv2.bitwise_and(safe_zone, cv2.bitwise_not(erase_mask))

    bg_pixels = img[bg_mask > 0]   # shape [N, 3] BGR

    if len(bg_pixels) >= 5:
        # Median màu từ tất cả background pixels → màu nền đặc trưng
        median_color = np.median(bg_pixels, axis=0).astype(np.uint8)
    else:
        # Fallback: không lấy được đủ pixel nền → dùng trắng
        median_color = np.array([255, 255, 255], dtype=np.uint8)
        logger.warning("Không đủ background pixel → dùng màu trắng")

    # Fill
    result[erase_mask > 0] = median_color
    logger.debug(f"Median fill: {median_color.tolist()} | bg_px={len(bg_pixels)}")

    # Trả về màu median để dùng ở spot removal
    return median_color


# ─────────────────────────────────────────────────────────────────
#  BƯỚC 4: SPOT REMOVAL — xóa chấm nhỏ còn sót
# ─────────────────────────────────────────────────────────────────

def _remove_residual_spots(
    result: np.ndarray,
    safe_zone: np.ndarray,
    max_spot_area: int = 120,
    darkness_threshold: int = 80,
) -> int:
    """
    Xóa các cụm pixel tối nhỏ (dấu câu, JPEG artifact) còn sót trong bubble.

    Thuật toán:
      1. Chuyển ảnh sang grayscale
      2. Sample màu nền hiện tại từ safe_zone (sau khi đã fill)
      3. Threshold: pixel nào tối hơn nền > darkness_threshold → "dark_mask"
      4. Connected Components: phân nhóm các cụm pixel tối riêng biệt
      5. Với mỗi cụm nhỏ (area < max_spot_area) bên trong safe_zone:
         → Fill bằng màu median của vùng lân cận (9x9px quanh cụm)

    Tại sao dùng Connected Components thay vì morphology?
      Morphology xóa theo hình dạng kernel → có thể xóa nhầm nét vẽ.
      Connected Components phân tích từng CỤM riêng lẻ → chỉ xóa cụm nhỏ.
      Cụm to (= chữ chưa xóa hết, hoặc nét vẽ bubble) → BỎ QUA.

    Args:
        result:             Ảnh đã qua median fill (sẽ bị modify in-place)
        safe_zone:          Mask vùng bên trong bubble (đã erode)
        max_spot_area:      Cụm nhỏ hơn số pixel này sẽ bị xóa (default 120px²)
        darkness_threshold: Chênh lệch tối hơn nền để coi là "chấm bẩn"

    Returns:
        Số cụm đã xóa
    """
    h, w = result.shape[:2]
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    # Sample màu nền hiện tại từ safe_zone
    safe_pixels = gray[safe_zone > 0]
    if len(safe_pixels) < 10:
        return 0
    bg_brightness = int(np.median(safe_pixels))

    # Ngưỡng: pixel tối hơn nền đủ nhiều → nghi là chữ sót/dấu câu
    dark_thresh = max(0, bg_brightness - darkness_threshold)

    # Binary mask: vùng tối bên trong safe_zone
    dark_mask = np.zeros((h, w), dtype=np.uint8)
    dark_mask[gray < dark_thresh] = 255
    dark_in_bubble = cv2.bitwise_and(dark_mask, safe_zone)

    if dark_in_bubble.max() == 0:
        return 0

    # Connected Components: phân nhóm các cụm tối riêng lẻ
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        dark_in_bubble, connectivity=8
    )

    n_removed = 0
    for label_id in range(1, num_labels):   # Bỏ qua label 0 = background
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if area >= max_spot_area:
            continue   # Cụm to → không phải dấu câu → bỏ qua

        # Lấy vị trí cụm
        cx = int(stats[label_id, cv2.CC_STAT_LEFT])
        cy = int(stats[label_id, cv2.CC_STAT_TOP])
        cw = int(stats[label_id, cv2.CC_STAT_WIDTH])
        ch = int(stats[label_id, cv2.CC_STAT_HEIGHT])

        # Sample màu nền từ vùng 15px xung quanh cụm (loại bỏ chính cụm đó)
        pad = 15
        rx1 = max(0, cx - pad);      ry1 = max(0, cy - pad)
        rx2 = min(w, cx + cw + pad); ry2 = min(h, cy + ch + pad)

        surround_mask = np.zeros((h, w), dtype=np.uint8)
        surround_mask[ry1:ry2, rx1:rx2] = 255
        # Loại bỏ chính cụm này khỏi vùng sample
        surround_mask[labels == label_id] = 0
        # Chỉ sample trong safe_zone
        surround_mask = cv2.bitwise_and(surround_mask, safe_zone)

        surround_pixels = result[surround_mask > 0]
        if len(surround_pixels) >= 3:
            fill_color = np.median(surround_pixels, axis=0).astype(np.uint8)
        else:
            # Fallback: dùng màu median toàn safe_zone
            bg_px = result[safe_zone > 0]
            fill_color = np.median(bg_px, axis=0).astype(np.uint8) if len(bg_px) > 0 else np.array([255,255,255], np.uint8)

        result[labels == label_id] = fill_color
        n_removed += 1
        logger.debug(f"  Spot {label_id}: area={area}px @ ({cx},{cy}) → fill {fill_color.tolist()}")

    return n_removed


# ─────────────────────────────────────────────────────────────────
#  PIPELINE CHÍNH
# ─────────────────────────────────────────────────────────────────

def process_and_save(
    img: np.ndarray,
    text_regions: list[dict],
    original_filename: str,
    bubbles: list[dict] = None,     # YOLO bubble list (để lấy polygon/bbox làm hàng rào)
    text_dilate_px: int = 5,        # Dilate text mask (ăn viền chữ)
    bubble_erode_px: int = 12,      # Erode bubble (hàng rào bảo vệ viền bubble — cần đủ sâu để qua viền đen)
    # Tương thích ngược với code cũ
    inpaint_radius: int = 8,
    mask_expand_px: int = 5,
) -> dict:
    """
    Pipeline xóa chữ 3 bước chuẩn Manhua:

      1. Text mask = polygon OCR + Otsu threshold + Dilate(5px)
      2. Safe zone = YOLO bubble polygon − Erode(5px)
      3. Erase mask = text_mask ∩ safe_zone
         Fill erase_mask bằng median color của background pixels

    Args:
        img:              Ảnh BGR gốc
        text_regions:     List dict từ PP-OCR (có keys: polygon, x,y,w,h, bubble_id)
        bubbles:          List bubble từ YOLO (có keys: polygon, x,y,w,h, class_name)
        text_dilate_px:   Dilate text mask (khuyến nghị 4-6px)
        bubble_erode_px:  Erode bubble fence (khuyến nghị 4-6px)
    """
    img_h, img_w = img.shape[:2]
    result = img.copy()

    if not text_regions:
        logger.warning("Không có text region nào!")
        return {
            "inpainted_img": result,
            "mask":          np.zeros((img_h, img_w), dtype=np.uint8),
            "saved_path":    None,
            "n_regions":     0,
            "method":        "skipped_empty",
        }

    # Tạo index bubble theo bubble_id
    bubble_by_id: dict[int, dict] = {}
    if bubbles:
        for idx, b in enumerate(bubbles):
            bubble_by_id[idx] = b

    # Nhóm text_region theo bubble_id
    groups: dict[int, list] = {}
    for region in text_regions:
        bid = region.get("bubble_id", -1)
        if bid not in groups:
            groups[bid] = []
        groups[bid].append(region)

    total_mask = np.zeros((img_h, img_w), dtype=np.uint8)
    n_filled = 0

    for bid, regions in groups.items():

        # ── Bước 1: Text mask (dilate) ──────────────────────────
        text_mask = _make_text_mask(img, regions, dilate_px=text_dilate_px)

        # ── Bước 2: Safe zone từ bubble polygon ─────────────────
        bubble_info = bubble_by_id.get(bid)
        if bubble_info:
            safe_zone = _make_bubble_safe_zone(
                img_h, img_w, bubble_info, erode_px=bubble_erode_px
            )
        else:
            # Không có YOLO bubble → safe zone = vùng bbox của các text region
            # (để tránh xóa nhầm ra ngoài)
            xs = [r.get("x", 0) for r in regions]
            ys = [r.get("y", 0) for r in regions]
            x2s = [r.get("x", 0) + r.get("w", 0) for r in regions]
            y2s = [r.get("y", 0) + r.get("h", 0) for r in regions]
            fx  = max(0, int(min(xs)) - 20)
            fy  = max(0, int(min(ys)) - 20)
            fx2 = min(img_w, int(max(x2s)) + 20)
            fy2 = min(img_h, int(max(y2s)) + 20)
            safe_zone = np.zeros((img_h, img_w), dtype=np.uint8)
            cv2.rectangle(safe_zone, (fx, fy), (fx2, fy2), 255, -1)

        # ── Bước 3: Erase mask = text_mask ∩ safe_zone ──────────
        erase_mask = cv2.bitwise_and(text_mask, safe_zone)

        if erase_mask.max() == 0:
            logger.debug(f"Bubble {bid}: không có vùng xóa sau khi clip safe_zone")
            continue

        # ── Bước 4: Median Fill ──────────────────────────────────
        _median_fill(img, result, erase_mask, safe_zone)

        total_mask = cv2.bitwise_or(total_mask, erase_mask)
        n_filled += 1

    logger.info(f"Median fill xong: {n_filled} bubble, "
                f"{total_mask.sum() // 255} px đã được xóa")

    # ── Bước 4: Spot Removal — xóa dấu câu/chấm nhỏ còn sót ────────
    # Dùng erode LỚN HƠN để safe_zone chắc chắn nằm xa viền đen bubble
    SPOT_ERODE = max(bubble_erode_px + 4, 16)   # Ít nhất 16px tính từ polygon
    all_safe_zone = np.zeros((img_h, img_w), dtype=np.uint8)
    if bubbles:
        for idx, b in enumerate(bubbles):
            z = _make_bubble_safe_zone(img_h, img_w, b, erode_px=SPOT_ERODE)
            all_safe_zone = cv2.bitwise_or(all_safe_zone, z)
    elif total_mask.max() > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
        all_safe_zone = cv2.dilate(total_mask, k)

    if all_safe_zone.max() > 0:
        # max_spot_area=30: chỉ xóa cụm < 30px² (= dấu chấm/phẩy thực sự nhỏ)
        n_spots = _remove_residual_spots(result, all_safe_zone, max_spot_area=30)
        if n_spots > 0:
            logger.info(f"Spot removal: xóa {n_spots} cụm pixel sót")

    # Lưu file
    stem    = Path(original_filename).stem
    ext     = Path(original_filename).suffix or ".jpg"
    ts      = datetime.now().strftime("%H%M%S")
    outname = f"{stem}_inpainted_{ts}{ext}"
    outpath = INPAINT_DIR / outname

    cv2.imwrite(str(outpath), result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info(f"Lưu: {outpath}")

    return {
        "inpainted_img": result,
        "mask":          total_mask,
        "saved_path":    str(outpath),
        "n_regions":     n_filled,
        "method":        "dilate+erode_fence+median_fill+spot_removal",
    }


# ─────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────

def build_text_mask(img_h, img_w, polygons, expand_px=5):
    """Wrapper tương thích ngược."""
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    for poly in polygons:
        if not poly or len(poly) < 3:
            continue
        pts = np.array(poly, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
    if expand_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (expand_px*2+1, expand_px*2+1))
        mask = cv2.dilate(mask, k)
    return mask


def inpaint_image(img, mask, method="telea", radius=8):
    """Wrapper tương thích ngược."""
    flags = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    return cv2.inpaint(img, mask, inpaintRadius=radius, flags=flags)


def img_to_base64(img: np.ndarray, quality: int = 90) -> str:
    """Convert numpy BGR image → base64 JPEG string."""
    import base64
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode("utf-8")
