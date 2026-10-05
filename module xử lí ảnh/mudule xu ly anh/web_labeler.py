"""
web_labeler.py — Công Cụ Gán Nhãn Đa Giác Nâng Cao Cho Truyện Tranh (V3)
=====================================================================
Tính năng nâng cấp toàn diện:
  1. Tọa độ chuẩn hóa theo tỷ lệ ảnh (Normalized 0.0 -> 1.0): Độc lập độ phân giải, chuẩn 100% cho YOLOv8 & React FE.
  2. Vẽ Đa Giác (Polygon Tool) tự do: Bắt trọn chữ nghiêng, bong bóng méo, chiêu thức thư pháp uốn lượn.
  3. Vẽ Chữ Nhật (Rectangle Tool) kéo thả nhanh cho bong bóng cơ bản.
  4. Upload ảnh trực tiếp: Tải ảnh từ máy tính hoặc kéo thả (Drag & Drop) vào tool.
  5. AI Gom Khung Chat (Auto-Bubble Cluster): Gom các dòng chữ con thành 1 KHUNG BONG BÓNG DUY NHẤT để dịch trọn câu.
  6. Multi-class: 💬 Bong bóng chat | 💥 Âm thanh / SFX | ✍️ Thư pháp / Chiêu thức.
  7. Xuất Dataset chuẩn YOLOv8 Segmentation (polygon normalized + data.yaml).
"""

import sys

# Fix Windows console encoding for UTF-8
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn
import os
import glob
import json
import shutil
import numpy as np
import cv2
from pathlib import Path
from paddleocr import PaddleOCR

app = FastAPI(title="Comic Label Tool v3 (Polygon & Normalized)")

# ==================== CẤU HÌNH ĐƯỜNG DẪN ====================
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
IMG_DIR    = r"d:\tool ghép ảnh\ket_qua_ghep_anh\chap02"
UPLOAD_DIR = os.path.join(BASE_DIR, "dataset", "uploads")
LABEL_FILE = os.path.join(BASE_DIR, "labels.txt")
EXPORT_DIR = os.path.join(BASE_DIR, "dataset", "yolo_export")
HTML_FILE  = os.path.join(BASE_DIR, "web_labeler.html")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Định nghĩa class
CLASSES = [
    {"id": 0, "name": "speech_bubble", "label": "💬 Bong bóng chat",  "color": "#e84118"},
    {"id": 1, "name": "sound_effect",  "label": "💥 Âm thanh / SFX",  "color": "#e67e22"},
    {"id": 2, "name": "calligraphy",   "label": "✍️ Thư pháp / Chiêu thức", "color": "#8e44ad"},
]

print("[INFO] Dang khoi tao PaddleOCR...")
ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
print("[INFO] Khoi tao PaddleOCR hoan tat!")


def get_all_image_paths() -> list:
    """Quét cả thư mục gốc và thư mục uploads"""
    paths = []
    for d in [IMG_DIR, UPLOAD_DIR]:
        if os.path.exists(d):
            found = glob.glob(os.path.join(d, "*.*"))
            paths.extend([p for p in found if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])
    # Loại bỏ trùng lặp nếu có và sắp xếp
    paths = list(dict.fromkeys(paths))
    paths.sort()
    return paths

image_paths = get_all_image_paths()


# ==================== LABEL I/O ====================

def load_labels() -> dict:
    """
    Đọc labels. Tự động tương thích ngược:
    Nếu dữ liệu cũ lưu pixel tuyệt đối (px > 1.0), sẽ tự động chuẩn hóa về [0..1]
    """
    labels = {}
    if os.path.exists(LABEL_FILE):
        with open(LABEL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    path = parts[0]
                    boxes = json.loads(parts[1])
                    labels[path] = boxes
    return labels


def save_labels(labels: dict):
    os.makedirs(os.path.dirname(LABEL_FILE), exist_ok=True)
    with open(LABEL_FILE, 'w', encoding='utf-8') as f:
        for path, data in labels.items():
            f.write(f"{path}\t{json.dumps(data, ensure_ascii=False)}\n")


def get_image_size(path: str):
    """Đọc W, H của ảnh"""
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is not None:
        h, w = img.shape[:2]
        return w, h
    return 1000, 1000


# ==================== API ENDPOINTS ====================

@app.get("/api/classes")
def get_classes():
    return {"classes": CLASSES}


@app.get("/api/info")
def get_info(index: int = 0):
    global image_paths
    if not image_paths:
        image_paths = get_all_image_paths()

    if index < 0 or index >= len(image_paths):
        return {"error": "Đã hết ảnh hoặc chưa có ảnh nào!"}

    path = image_paths[index]
    labels = load_labels()
    saved_data = labels.get(path, None)

    # Đọc W, H ảnh thực tế
    w, h = get_image_size(path)

    # Chuyển đổi nhãn sang chuẩn Normalized [0..1] nếu là dạng pixel cũ
    normalized_boxes = []
    if saved_data:
        for item in saved_data:
            b = dict(item)
            # Chuẩn hóa polygon
            poly = b.get("polygon")
            if poly and len(poly) > 0:
                # Kiểm tra nếu tọa độ > 1.0 nghĩa là pixel tuyệt đối
                if any(pt[0] > 1.0 or pt[1] > 1.0 for pt in poly):
                    poly = [[round(pt[0] / w, 6), round(pt[1] / h, 6)] for pt in poly]
                b["polygon"] = poly
            
            # Chuẩn hóa box [x, y, bw, bh]
            box = b.get("box", [0, 0, 0, 0])
            if any(val > 1.0 for val in box):
                box = [
                    round(box[0] / w, 6),
                    round(box[1] / h, 6),
                    round(box[2] / w, 6),
                    round(box[3] / h, 6),
                ]
            b["box"] = box
            b["class_id"] = b.get("class_id", 0)
            normalized_boxes.append(b)

    return {
        "index": index,
        "total": len(image_paths),
        "filename": os.path.basename(path),
        "path": path,
        "width": w,
        "height": h,
        "has_saved_labels": saved_data is not None,
        "boxes": normalized_boxes
    }


@app.get("/api/image/{index}")
def get_image(index: int):
    global image_paths
    if 0 <= index < len(image_paths):
        return FileResponse(image_paths[index])
    return JSONResponse({"error": "index out of range"}, status_code=404)


@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    """Upload ảnh trực tiếp từ trình duyệt vào dataset/uploads"""
    global image_paths
    saved_paths = []
    for file in files:
        filename = os.path.basename(file.filename)
        base, ext = os.path.splitext(filename)
        save_path = os.path.join(UPLOAD_DIR, filename)
        
        # Tránh ghi đè file cũ nếu trùng tên (giữ nguyên dữ liệu cũ)
        counter = 1
        while os.path.exists(save_path):
            save_path = os.path.join(UPLOAD_DIR, f"{base}_{counter}{ext}")
            counter += 1
            
        with open(save_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        saved_paths.append(save_path)

    image_paths = get_all_image_paths()
    new_idx = 0
    if saved_paths and saved_paths[0] in image_paths:
        new_idx = image_paths.index(saved_paths[0])

    return {
        "status": "ok",
        "uploaded": len(saved_paths),
        "new_index": new_idx,
        "total": len(image_paths)
    }


@app.post("/api/set_folder")
async def set_folder(request: Request):
    global IMG_DIR, image_paths
    data = await request.json()
    new_folder = data.get("folder", "").strip()
    
    # Loại bỏ ngoặc kép nếu user lỡ copy paste cả dấu ngoặc kép của Windows
    new_folder = new_folder.strip('"').strip("'")
    
    if not new_folder or not os.path.exists(new_folder) or not os.path.isdir(new_folder):
        return {"error": f"Thư mục không tồn tại: {new_folder}"}
        
    IMG_DIR = new_folder
    image_paths = get_all_image_paths()
    return {"status": "ok", "total": len(image_paths)}


@app.post("/api/predict_bubble/{index}")
def predict_bubble_clusters(index: int):
    """
    AI GOM KHUNG BONG BÓNG (Auto-Bubble Cluster):
    Gom các dòng chữ con ở gần nhau thành 1 KHUNG BONG BÓNG DUY NHẤT.
    Tọa độ chuẩn hóa theo tỷ lệ ảnh [0.0 - 1.0].
    """
    if index < 0 or index >= len(image_paths):
        return {"boxes": []}
    path = image_paths[index]
    img_cv = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img_cv is None:
        return {"boxes": []}
    
    img_h, img_w = img_cv.shape[:2]
    result = ocr.ocr(img_cv, cls=True)

    if not result or not result[0]:
        return {"boxes": []}

    # Bóc tách các line từ OCR
    raw_lines = []
    for line in result[0]:
        poly = line[0]
        text = line[1][0]
        conf = float(line[1][1])
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        raw_lines.append({
            "poly": poly,
            "bbox": (x1, y1, x2, y2),
            "text": text,
            "conf": conf
        })

    # Gom cụm các dòng chữ gần nhau
    clusters = []
    used = set()

    for i in range(len(raw_lines)):
        if i in used:
            continue
        cluster = [i]
        used.add(i)

        for j in range(len(raw_lines)):
            if j in used:
                continue
            all_b = [raw_lines[k]["bbox"] for k in cluster]
            cx1 = min(b[0] for b in all_b)
            cy1 = min(b[1] for b in all_b)
            cx2 = max(b[2] for b in all_b)
            cy2 = max(b[3] for b in all_b)
            
            jx1, jy1, jx2, jy2 = raw_lines[j]["bbox"]
            jh = jy2 - jy1
            ch = cy2 - cy1
            avg_h = max(15, (jh + ch) / 2)

            dx = max(0, max(cx1, jx1) - min(cx2, jx2))
            dy = max(0, max(cy1, jy1) - min(cy2, jy2))

            if dx < avg_h * 1.8 and dy < avg_h * 1.5:
                cluster.append(j)
                used.add(j)

        clusters.append(cluster)

    # Chuyển mỗi cluster thành 1 bong bóng chat hoàn chỉnh
    bubble_boxes = []
    for cl in clusters:
        cl_sorted = sorted(cl, key=lambda k: raw_lines[k]["bbox"][1])
        full_text = "".join(raw_lines[k]["text"] for k in cl_sorted)

        all_pts = []
        for k in cl_sorted:
            all_pts.extend(raw_lines[k]["poly"])

        all_x = [p[0] for p in all_pts]
        all_y = [p[1] for p in all_pts]
        pad = 12
        min_x = max(0, min(all_x) - pad)
        min_y = max(0, min(all_y) - pad)
        max_x = min(img_w, max(all_x) + pad)
        max_y = min(img_h, max(all_y) + pad)

        polygon_px = [
            [min_x, min_y],
            [max_x, min_y],
            [max_x, max_y],
            [min_x, max_y]
        ]

        norm_poly = [[round(p[0] / img_w, 6), round(p[1] / img_h, 6)] for p in polygon_px]
        norm_box = [
            round(min_x / img_w, 6),
            round(min_y / img_h, 6),
            round((max_x - min_x) / img_w, 6),
            round((max_y - min_y) / img_h, 6)
        ]

        bubble_boxes.append({
            "box": norm_box,
            "polygon": norm_poly,
            "text": full_text,
            "class_id": 0,
            "confidence": 0.95
        })

    return {"boxes": bubble_boxes, "count": len(bubble_boxes)}


@app.post("/api/ocr_region/{index}")
async def ocr_region(index: int, request: Request):
    """
    Nhận diện chữ (OCR) trên một vùng cụ thể (crop box).
    Dùng khi user muốn lấy text tự động cho một khung vừa vẽ/chỉnh sửa.
    """
    data = await request.json()
    box = data.get("box") # [nx, ny, nw, nh]
    
    if not box or index < 0 or index >= len(image_paths):
        return {"text": ""}
        
    path = image_paths[index]
    img_cv = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img_cv is None:
        return {"text": ""}
        
    img_h, img_w = img_cv.shape[:2]
    
    # Giải chuẩn hóa tọa độ
    x = int(box[0] * img_w)
    y = int(box[1] * img_h)
    w = int(box[2] * img_w)
    h = int(box[3] * img_h)
    
    # Mở rộng nhẹ vùng crop thêm 5px để AI dễ đọc viền
    pad = 5
    x = max(0, x - pad)
    y = max(0, y - pad)
    w = min(img_w - x, w + pad*2)
    h = min(img_h - y, h + pad*2)
    
    if w <= 0 or h <= 0:
        return {"text": ""}
        
    cropped = img_cv[y:y+h, x:x+w]
    
    result = ocr.ocr(cropped, cls=False)
    if not result or not result[0]:
        return {"text": ""}
        
    # Gom chữ lại (PaddleOCR có thể trả về nhiều dòng trong vùng crop)
    lines = []
    # result[0] chứa list các dòng, mỗi dòng: [poly, [text, conf]]
    # Sort từ trên xuống dưới theo Y
    sorted_res = sorted(result[0], key=lambda k: k[0][0][1])
    for line in sorted_res:
        lines.append(line[1][0])
        
    full_text = "".join(lines)
    return {"text": full_text}


@app.post("/api/save/{index}")
async def save_image_labels(index: int, request: Request):
    data = await request.json()
    path = image_paths[index]
    labels = load_labels()
    labels[path] = data.get("boxes", [])
    save_labels(labels)
    return {"status": "ok", "saved": len(labels[path])}


@app.post("/api/export_yolo")
async def export_yolo():
    """
    Xuất dataset chuẩn YOLOv8 Segmentation:
    dataset/yolo_export/
      images/train/
      labels/train/  <- file .txt: class_id nx1 ny1 nx2 ny2 ... (tọa độ tỷ lệ 0..1)
      data.yaml
    """
    labels = load_labels()
    if not labels:
        return {"error": "Chưa có nhãn nào được lưu để xuất!"}

    img_out = os.path.join(EXPORT_DIR, "images", "train")
    lbl_out = os.path.join(EXPORT_DIR, "labels", "train")
    os.makedirs(img_out, exist_ok=True)
    os.makedirs(lbl_out, exist_ok=True)

    exported = 0
    skipped  = 0

    for img_path, boxes in labels.items():
        if not boxes:
            skipped += 1
            continue
        if not os.path.exists(img_path):
            skipped += 1
            continue

        # Copy ảnh
        img_name = os.path.basename(img_path)
        dst_img  = os.path.join(img_out, img_name)
        shutil.copy2(img_path, dst_img)

        # File txt
        stem = Path(img_name).stem
        lbl_path = os.path.join(lbl_out, stem + ".txt")

        with open(lbl_path, 'w', encoding='utf-8') as lf:
            for item in boxes:
                class_id = item.get("class_id", 0)
                poly = item.get("polygon")
                
                if poly and len(poly) >= 3:
                    pts = poly
                else:
                    bx, by, bw, bh = item["box"]
                    pts = [
                        [bx, by],
                        [bx + bw, by],
                        [bx + bw, by + bh],
                        [bx, by + bh]
                    ]

                coord_strs = []
                for pt in pts:
                    nx = max(0.0, min(1.0, float(pt[0])))
                    ny = max(0.0, min(1.0, float(pt[1])))
                    coord_strs.extend([f"{nx:.6f}", f"{ny:.6f}"])

                lf.write(f"{class_id} {' '.join(coord_strs)}\n")

        exported += 1

    # Tạo data.yaml
    class_names = [c["name"] for c in CLASSES]
    yaml_content = f"""# YOLOv8 Segmentation Dataset
# Tự động sinh bởi Comic Label Tool v3
# Đã chuẩn hóa tỉ lệ [0..1]
path: {EXPORT_DIR}
train: images/train
val:   images/train   # Dùng chung hoặc chia tập val riêng

nc: {len(CLASSES)}
names: {json.dumps(class_names, ensure_ascii=False)}
"""
    yaml_path = os.path.join(EXPORT_DIR, "data.yaml")
    with open(yaml_path, 'w', encoding='utf-8') as yf:
        yf.write(yaml_content)

    return {
        "status": "ok",
        "exported": exported,
        "skipped": skipped,
        "output_dir": EXPORT_DIR,
        "data_yaml": yaml_path,
        "classes": class_names
    }


# ==================== GIAO DIỆN WEB ====================

@app.get("/")
def index():
    classes_json = json.dumps(CLASSES, ensure_ascii=False)
    if not os.path.exists(HTML_FILE):
        return HTMLResponse("<h1>Không tìm thấy web_labeler.html</h1>", status_code=500)
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read().replace("__CLASSES_JSON__", classes_json)
    return HTMLResponse(content=html)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
