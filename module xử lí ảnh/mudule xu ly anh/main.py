"""
main.py — FastAPI Server: Pipeline Dịch Truyện Tranh Tiếng Trung
================================================================
Luồng xử lý đầy đủ 1 ảnh trang truyện:

  React FE Upload ảnh
      ↓
  POST /process-page
      ↓
  Stage 1: YOLOv8 Segmentation (model đã train từ web_labeler)
           → Phát hiện vùng: speech_bubble / sound_effect / calligraphy
      ↓
  Stage 2: PP-OCRv4 (đọc chữ Hán trong từng bubble YOLO)
           → text + tọa độ polygon từng ký tự
      ↓
  Stage 3: pypinyin → Pinyin chuẩn (nǐ hǎo)
           + 4-Lớp dịch thuật (Names→VietPhrase→LuatNhan→PhienAm)
           → Tiếng Việt phong cách tiên hiệp
      ↓
  Stage 4: OpenCV Inpainting
           → Xóa chữ Hán bằng mask polygon
           → Lưu ảnh sạch vào dataset/inpainted/
      ↓
  Trả về JSON:
    - image_base64:    Ảnh gốc (để hiển thị)
    - inpainted_b64:   Ảnh đã xóa chữ
    - inpainted_path:  Đường dẫn file đã lưu
    - bubbles:         List vùng YOLO detect được (class, polygon)
    - texts:           List {text_zh, pinyin, vi, bbox} → dùng cho hover popup
"""

import sys
import os

# Fix Windows console encoding
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import cv2
import numpy as np
import base64
import logging
import hashlib
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from pipeline import get_pipeline
from translator import get_translator
from inpainter import process_and_save, img_to_base64
from text_renderer import render_all_bubbles

# ===================== LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ===================== APP =====================
app = FastAPI(
    title="Comic Translation API",
    description="Pipeline dịch truyện tranh Trung → Việt phong cách tiên hiệp",
    version="2.0"
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi frontend gọi API (React, Vue, HTML tĩnh)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== KHỞI TẠO SINGLETON =====================
print("[INFO] Dang khoi tao OCR Pipeline (YOLOv8 + PP-OCRv4)...")
pipeline   = get_pipeline()
print("[INFO] OCR Pipeline san sang!")

print("[INFO] Dang nap bo tu dien 4 lop (Names + VietPhrase + LuatNhan + PhienAm)...")
translator = get_translator()
print("[INFO] Bo tu dien san sang!")


# ===================== API ENDPOINT CHÍNH =====================

@app.post("/extract-text")
@app.post("/process-page")
async def process_page(file: UploadFile = File(...)):
    """
    Xử lý 1 trang truyện tranh:
      1. YOLO detect vùng bubble (speech_bubble / sound_effect / calligraphy)
      2. PP-OCR đọc chữ Hán trong từng bubble
      3. Dịch + Pinyin qua Engine 4 lớp
      4. Inpainting (xóa chữ, lưu ảnh)
      5. Trả JSON đầy đủ về FE
    """
    # Đọc ảnh từ upload
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Không thể đọc file ảnh!")

    img_h, img_w = img.shape[:2]
    original_filename = file.filename or "page.jpg"

    # ============ STAGE 1 + 2: YOLO → PP-OCR ============
    logger.info(f"Bắt đầu xử lý: {original_filename} ({img_w}x{img_h})")
    # detect_floating=False: KHÔNG OCR chữ nằm ngoài YOLO bubble
    # (floating text như SFX, âm thanh ngoài bong bóng — xử lý sau)
    ocr_result = pipeline.process(img, detect_floating=False)

    bubbles = ocr_result["bubbles"]   # YOLO bubbles (multi-class)
    all_texts = ocr_result["texts"]   # Text từ OCR trong YOLO bubble
    mode    = ocr_result["mode"]
    stats   = ocr_result["stats"]

    # Chỉ lấy text nằm TRONG YOLO bubble (bubble_id >= 0)
    # Bỏ qua floating text (bubble_id = -1) — chưa xử lý
    texts = [t for t in all_texts if t.get("bubble_id", -1) >= 0]

    logger.info(f"OCR xong: {len(bubbles)} bubbles, {len(texts)} text regions (trong bubble)")

    # ============ STAGE 3: DỊCH + PINYIN ============
    # Gom text theo từng bubble để dịch trọn câu (không dịch từng dòng lẻ)
    bubble_translations = {}  # bubble_id → {text_zh, pinyin, vi}

    # Gom text theo bubble_id
    bubble_texts: dict[int, list] = {}
    for t in texts:
        bid = t.get("bubble_id", -1)
        if bid not in bubble_texts:
            bubble_texts[bid] = []
        bubble_texts[bid].append(t)

    # Dịch từng bubble (gom toàn bộ dòng chữ trong 1 bubble)
    for bid, regions in bubble_texts.items():
        # Sắp xếp từ trên xuống dưới (đọc theo thứ tự manga: thường phải → trái)
        regions_sorted = sorted(regions, key=lambda r: (r.get("y", 0), r.get("x", 0)))
        
        # Lọc bỏ các dòng chữ Hán bị OCR nhận diện trùng lặp (vd: bóng mờ)
        unique_texts = []
        for r in regions_sorted:
            txt = r["text"].strip()
            if not txt: continue
            if not unique_texts or unique_texts[-1] != txt:
                unique_texts.append(txt)
                
        full_text_zh = "".join(unique_texts)

        if not full_text_zh.strip():
            continue

        trans = translator.translate(full_text_zh)
        bubble_translations[bid] = {
            "text_zh":   trans["original"],
            "pinyin":    trans["pinyin"],
            "vi":        trans["vi"],
            "method":    trans["method"],
            "bubble_id": bid,
        }

    logger.info(f"Dịch xong: {len(bubble_translations)} bubbles")

    # Gán thông tin dịch vào từng text region
    enriched_texts = []
    for t in texts:
        bid   = t.get("bubble_id", -1)
        trans = bubble_translations.get(bid, {})
        enriched_texts.append({
            # Thông tin vị trí (pixel tuyệt đối trong ảnh gốc)
            "x":         t.get("x", 0),
            "y":         t.get("y", 0),
            "w":         t.get("w", 0),
            "h":         t.get("h", 0),
            "polygon":   t.get("polygon", []),
            # Thông tin class
            "class_id":   t.get("class_id", 0),
            "class_name": t.get("class_name", "speech_bubble"),
            "bubble_id":  bid,
            # Nội dung OCR
            "text":       t.get("text", ""),        # Backward compatibility cho React
            "text_zh":    t.get("text", ""),
            "confidence": t.get("confidence", 0),
            # Bản dịch (từ bubble cha)
            "pinyin":     trans.get("pinyin", ""),
            "vi":         trans.get("vi", t.get("text", "")),
            "full_zh":    trans.get("text_zh", t.get("text", "")),
        })

    # ============ STAGE 4: INPAINTING (Xóa chữ) ============
    # Chỉ xóa chữ trong YOLO bubble (texts đã được lọc bubble_id >= 0)
    inpaint_result = process_and_save(
        img=img,
        text_regions=texts,
        bubbles=bubbles,
        original_filename=original_filename,
        text_dilate_px=5,
        bubble_erode_px=12,
    )

    inpainted_img  = inpaint_result["inpainted_img"]
    inpainted_path = inpaint_result.get("saved_path", "")
    n_inpainted    = inpaint_result["n_regions"]

    logger.info(f"Inpainting xong: {n_inpainted} vùng đã xóa → {inpainted_path}")

    # ============ STAGE 5: RENDER CHỮ TIẾNG VIỆT VÀO ẢNH ============
    rendered_img = render_all_bubbles(
        img=inpainted_img,
        bubbles=bubbles,
        texts=texts,
        bubble_translations=bubble_translations,
        original_img=img,
    )
    logger.info("Render chữ tiếng Việt xong")

    # ============ ENCODE IMAGES → BASE64 ============
    orig_b64      = img_to_base64(img, quality=88)
    inpainted_b64 = img_to_base64(inpainted_img, quality=88)
    rendered_b64  = img_to_base64(rendered_img, quality=88)

    return {
        "status":          "ok",
        "filename":        original_filename,
        "width":           img_w,
        "height":          img_h,
        "mode":            mode,
        # Ảnh
        "image_base64":    orig_b64,
        "inpainted_b64":   inpainted_b64,
        "rendered_b64":    rendered_b64,       # Ảnh đã đắp chữ tiếng Việt
        "inpainted_path":  inpainted_path,
        # Dữ liệu
        "bubbles":         bubbles,
        "texts":           enriched_texts,
        "bubble_translations": list(bubble_translations.values()),
        "stats":           stats,
        "n_inpainted":     n_inpainted,
    }


# ===================== PREVIEW MODEL (CHỈ YOLO, KHÔNG OCR) =====================

# Màu sắc cho từng class (BGR cho OpenCV)
_CLASS_COLORS_BGR = {
    "speech_bubble": (24,  65,  232),
    "sound_effect":  (34,  126, 230),
    "calligraphy":   (173, 68,  142),
    "floating_text": (50,  205, 50),
}
_CLASS_LABELS_VI = {
    "speech_bubble": "Bong bong chat",
    "sound_effect":  "SFX / Am thanh",
    "calligraphy":   "Thu phap",
    "floating_text": "Chu noi",
}

PREVIEW_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Preview YOLO Model</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0a0d14; color: #e2e8f0; min-height: 100vh; }
  header { background: #0f1729; border-bottom: 1px solid #1e2a45; padding: 14px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 17px; font-weight: 700; color: #f59e0b; }
  .badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; background: rgba(245,158,11,.15); border: 1px solid rgba(245,158,11,.3); color: #f59e0b; }
  .back { margin-left: auto; font-size: 12px; color: #6366f1; text-decoration: none; font-weight: 600; }
  .layout { display: flex; height: calc(100vh - 57px); }
  .sidebar { width: 310px; flex-shrink: 0; background: #0d1525; border-right: 1px solid #1e2a45; padding: 18px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
  .lbl { font-size: 11px; font-weight: 700; color: #818cf8; text-transform: uppercase; letter-spacing: .8px; display: block; margin-bottom: 6px; }
  input[type=file] { display: block; width: 100%; padding: 9px; border-radius: 7px; background: #1e2a45; color: #e2e8f0; border: 1px solid #2d3f60; font-size: 12px; cursor: pointer; }
  .conf-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
  .conf-row input[type=range] { flex: 1; accent-color: #f59e0b; }
  .conf-val { font-size: 13px; font-weight: 700; color: #f59e0b; width: 36px; text-align: right; }
  .hint { font-size: 11px; color: #475569; margin-top: 4px; }
  .btn { width: 100%; padding: 12px; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; cursor: pointer; transition: all .2s; background: linear-gradient(135deg, #f59e0b, #d97706); color: #0a0d14; }
  .btn:not(:disabled):hover { filter: brightness(1.1); transform: translateY(-1px); }
  .btn:disabled { opacity: .4; cursor: not-allowed; }
  .status { padding: 10px 12px; border-radius: 8px; font-size: 12px; line-height: 1.6; background: #131b30; border-left: 3px solid #f59e0b; color: #94a3b8; }
  .status.loading { border-color: #f59e0b; color: #fcd34d; }
  .status.success { border-color: #10b981; color: #6ee7b7; }
  .status.error   { border-color: #ef4444; color: #fca5a5; }
  .view-toggle { display: flex; gap: 6px; }
  .tbtn { flex: 1; padding: 8px; border: 1px solid #2d3f60; border-radius: 6px; background: #131b30; color: #64748b; font-size: 12px; cursor: pointer; transition: all .15s; font-weight: 600; }
  .tbtn.active { background: #1e2a45; border-color: #f59e0b; color: #f59e0b; }
  .stat-box { background: #131b30; border: 1px solid #1e2a45; border-radius: 8px; padding: 12px; }
  .stat-box .title { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; font-weight: 700; }
  .stat-row { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
  .stat-row span:last-child { font-weight: 700; color: #f59e0b; }
  .legend { display: flex; flex-direction: column; gap: 6px; }
  .li { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #94a3b8; }
  .dot { width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }
  .viewer { flex: 1; overflow: auto; background: #070b12; display: flex; align-items: flex-start; justify-content: center; padding: 24px; }
  #workspace { position: relative; display: inline-block; box-shadow: 0 15px 50px rgba(0,0,0,.7); }
  #main-img { display: block; max-width: 100%; }
  .spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid rgba(245,158,11,.3); border-top-color: #f59e0b; border-radius: 50%; animation: spin .8s linear infinite; margin-right: 6px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<header>
  <h1>🔍 Preview YOLO Model</h1>
  <span class="badge">CHI YOLO · KHONG OCR · KHONG DICH</span>
  <a class="back" href="/">← Ve trang dich thuat</a>
</header>
<div class="layout">
  <div class="sidebar">
    <div>
      <span class="lbl">1. Chon anh truyen tranh</span>
      <input type="file" id="fileInput" accept="image/*">
    </div>
    <div>
      <span class="lbl">2. Confidence threshold</span>
      <div class="conf-row">
        <input type="range" id="confSlider" min="5" max="90" value="30" step="5">
        <span class="conf-val" id="confVal">30%</span>
      </div>
      <div class="hint">Thap → phat hien nhieu hon. Cao → chinh xac hon.</div>
    </div>
    <button class="btn" id="runBtn" onclick="runPreview()" disabled>🔍 Chay YOLO Preview</button>
    <div class="status" id="statusBox">Chon anh de bat dau...</div>
    <div id="toggleGroup" style="display:none">
      <span class="lbl">Xem anh:</span>
      <div class="view-toggle">
        <button class="tbtn active" id="btnOrig" onclick="switchView('orig')">📷 Anh goc</button>
        <button class="tbtn" id="btnPrev" onclick="switchView('preview')">🎯 Ket qua YOLO</button>
      </div>
    </div>
    <div class="stat-box" id="statBox" style="display:none">
      <div class="title">📊 Ket qua phat hien</div>
      <div class="stat-row"><span>Tong bong bong</span><span id="stTotal">—</span></div>
      <div id="stClasses"></div>
    </div>
    <div>
      <span class="lbl">Chu thich mau:</span>
      <div class="legend">
        <div class="li"><div class="dot" style="background:#e84118"></div>💬 Speech Bubble</div>
        <div class="li"><div class="dot" style="background:#e67e22"></div>💥 Sound Effect</div>
        <div class="li"><div class="dot" style="background:#8e44ad"></div>✍️ Calligraphy</div>
        <div class="li"><div class="dot" style="background:#32cd32"></div>🌊 Floating Text</div>
      </div>
    </div>
  </div>
  <div class="viewer">
    <div id="workspace">
      <img id="main-img" src="" style="display:none" alt="Preview">
    </div>
  </div>
</div>
<script>
  const fileInput  = document.getElementById('fileInput');
  const runBtn     = document.getElementById('runBtn');
  const confSlider = document.getElementById('confSlider');
  const confVal    = document.getElementById('confVal');
  const statusBox  = document.getElementById('statusBox');
  const mainImg    = document.getElementById('main-img');
  let origB64 = null, previewB64 = null;

  confSlider.addEventListener('input', () => { confVal.textContent = confSlider.value + '%'; });

  fileInput.addEventListener('change', () => {
    if (!fileInput.files.length) return;
    runBtn.disabled = false;
    const reader = new FileReader();
    reader.onload = e => {
      origB64 = e.target.result; previewB64 = null;
      mainImg.src = origB64; mainImg.style.display = 'block';
      document.getElementById('toggleGroup').style.display = 'none';
      document.getElementById('statBox').style.display = 'none';
    };
    reader.readAsDataURL(fileInput.files[0]);
    setStatus('Nhan nut de chay YOLO Preview...', '');
  });

  function setStatus(msg, type) { statusBox.className = 'status ' + (type || ''); statusBox.innerHTML = msg; }

  function switchView(v) {
    document.getElementById('btnOrig').classList.toggle('active', v === 'orig');
    document.getElementById('btnPrev').classList.toggle('active', v === 'preview');
    mainImg.src = v === 'orig' ? origB64 : 'data:image/jpeg;base64,' + previewB64;
  }

  async function runPreview() {
    if (!fileInput.files.length) return;
    runBtn.disabled = true;
    setStatus('<span class="spinner"></span>Dang chay YOLO...', 'loading');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const conf = (parseInt(confSlider.value) / 100).toFixed(2);
    try {
      const res = await fetch('/preview-model?conf=' + conf, { method: 'POST', body: formData });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Loi server'); }
      const data = await res.json();
      previewB64 = data.preview_b64;
      origB64 = 'data:image/jpeg;base64,' + data.image_base64;
      switchView('preview');
      document.getElementById('toggleGroup').style.display = 'block';
      document.getElementById('statBox').style.display = 'block';
      document.getElementById('stTotal').textContent = data.n_bubbles;
      document.getElementById('stClasses').innerHTML = Object.entries(data.class_counts || {})
        .map(([k,v]) => `<div class="stat-row"><span>${k}</span><span>${v}</span></div>`).join('');
      const cls = Object.entries(data.class_counts || {}).map(([k,v])=>`${k}:${v}`).join(' | ');
      setStatus(`✅ Phat hien <b>${data.n_bubbles}</b> bong bong<br>📐 ${data.width}×${data.height}px<br>${cls}`, 'success');
    } catch(e) { setStatus('❌ ' + e.message, 'error'); }
    finally { runBtn.disabled = false; }
  }
</script>
</body>
</html>"""


@app.get("/preview")
async def preview_page():
    """Trang giao diện xem kết quả YOLO model (không OCR, không dịch)."""
    return HTMLResponse(content=PREVIEW_HTML)


@app.post("/preview-model")
async def preview_model(file: UploadFile = File(...), conf: float = 0.30):
    """
    Chỉ chạy YOLOv8 detect bong bóng, vẽ màu lên ảnh rồi trả về.
    KHÔNG chạy OCR, KHÔNG dịch, KHÔNG Inpainting.
    """
    contents = await file.read()
    nparr    = np.frombuffer(contents, np.uint8)
    img      = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Khong the doc file anh!")

    img_h, img_w = img.shape[:2]

    if not pipeline.yolo_available:
        raise HTTPException(
            status_code=503,
            detail="YOLO model chua duoc load! Kiem tra lai YOLO_MODEL_PATH trong pipeline.py."
        )

    # Tạm thời đổi conf rồi khôi phục lại sau
    original_conf = pipeline.yolo_conf
    pipeline.yolo_conf = conf
    logger.info(f"[preview-model] conf={conf:.0%} | {file.filename} ({img_w}x{img_h})")
    bubbles = pipeline.detect_bubbles(img)
    pipeline.yolo_conf = original_conf
    logger.info(f"[preview-model] → {len(bubbles)} bong bong")

    # Vẽ kết quả lên ảnh
    vis     = img.copy()
    overlay = img.copy()

    for i, b in enumerate(bubbles):
        cls    = b.get("class_name", "speech_bubble")
        color  = _CLASS_COLORS_BGR.get(cls, (200, 200, 200))
        conf_b = b.get("confidence", 0)
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]

        poly = b.get("polygon")
        if poly and len(poly) >= 3:
            pts = np.array(poly, dtype=np.int32)
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(vis, [pts], isClosed=True, color=color, thickness=3)
        else:
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(vis, (x, y), (x + w, y + h), color, 3)

        label = f"#{i+1} {_CLASS_LABELS_VI.get(cls, cls)} {conf_b:.0%}"
        lx, ly = x, max(y - 10, 20)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(vis, (lx, ly - th - 6), (lx + tw + 8, ly + 2), color, -1)
        cv2.putText(vis, label, (lx + 4, ly - 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    vis = cv2.addWeighted(vis, 0.82, overlay, 0.18, 0)

    preview_b64 = img_to_base64(vis, quality=90)
    orig_b64    = img_to_base64(img, quality=88)

    class_counts: dict[str, int] = {}
    for b in bubbles:
        c = b.get("class_name", "unknown")
        class_counts[c] = class_counts.get(c, 0) + 1

    return {
        "status":       "ok",
        "filename":     file.filename,
        "width":        img_w,
        "height":       img_h,
        "n_bubbles":    len(bubbles),
        "class_counts": class_counts,
        "bubbles":      bubbles,
        "image_base64": orig_b64,
        "preview_b64":  preview_b64,
    }


# ===================== GIAO DIỆN WEB =====================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎌 Truyện Tranh Dịch Thuật — Tiên Hiệp</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', sans-serif; background: #0a0d14; color: #e2e8f0; height: 100vh; display: flex; flex-direction: column; }

  /* HEADER */
  header {
    background: linear-gradient(90deg, #0f1729 0%, #131b30 100%);
    border-bottom: 1px solid #1e2a45;
    padding: 12px 24px;
    display: flex; align-items: center; gap: 16px; flex-shrink: 0;
  }
  header h1 { font-size: 18px; font-weight: 700; color: #818cf8; }
  .badge {
    padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
    background: rgba(129,140,248,.15); border: 1px solid rgba(129,140,248,.3); color: #818cf8;
  }

  /* MAIN LAYOUT */
  .layout { flex: 1; display: flex; overflow: hidden; }

  /* SIDEBAR */
  .sidebar {
    width: 300px; flex-shrink: 0; background: #0d1525;
    border-right: 1px solid #1e2a45; display: flex; flex-direction: column;
    padding: 16px; gap: 14px; overflow-y: auto;
  }
  .upload-zone {
    border: 2px dashed #2d3f60; border-radius: 10px; padding: 24px 16px;
    text-align: center; cursor: pointer; transition: all .2s;
  }
  .upload-zone:hover { border-color: #818cf8; background: rgba(129,140,248,.05); }
  .upload-zone input { display: none; }
  .upload-zone .icon { font-size: 32px; margin-bottom: 8px; }
  .upload-zone p { font-size: 12px; color: #64748b; }

  .btn {
    width: 100%; padding: 11px; border: none; border-radius: 8px;
    font-size: 13px; font-weight: 600; cursor: pointer; transition: all .2s;
  }
  .btn:disabled { opacity: .4; cursor: not-allowed; }
  .btn-primary {
    background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff;
  }
  .btn-primary:not(:disabled):hover { filter: brightness(1.1); transform: translateY(-1px); }
  .btn-secondary {
    background: #1e2a45; color: #94a3b8; border: 1px solid #2d3f60;
  }
  .btn-secondary:not(:disabled):hover { background: #253556; }

  .status {
    padding: 10px 12px; border-radius: 8px; font-size: 12px;
    background: #131b30; border-left: 3px solid #6366f1; color: #94a3b8;
    line-height: 1.5;
  }
  .status.loading { border-color: #f59e0b; color: #fcd34d; }
  .status.success { border-color: #10b981; color: #6ee7b7; }
  .status.error   { border-color: #ef4444; color: #fca5a5; }

  .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat-card {
    background: #131b30; border: 1px solid #1e2a45; border-radius: 8px;
    padding: 10px; text-align: center;
  }
  .stat-card .val { font-size: 20px; font-weight: 700; color: #818cf8; }
  .stat-card .lbl { font-size: 10px; color: #475569; margin-top: 2px; }

  /* VIEW TOGGLE */
  .view-toggle {
    display: flex; gap: 6px;
  }
  .toggle-btn {
    flex: 1; padding: 7px; border: 1px solid #2d3f60; border-radius: 6px;
    background: #131b30; color: #64748b; font-size: 12px; cursor: pointer;
    transition: all .15s; font-weight: 600;
  }
  .toggle-btn.active { background: #1e2a45; border-color: #818cf8; color: #818cf8; }

  /* VIEWER */
  .viewer {
    flex: 1; overflow: auto; background: #070b12;
    display: flex; align-items: flex-start; justify-content: center; padding: 24px;
  }
  #workspace {
    position: relative; display: inline-block;
    box-shadow: 0 15px 50px rgba(0,0,0,.7); border-radius: 4px;
  }
  #main-img { display: block; max-width: 100%; }
  #overlays { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }

  /* TEXT OVERLAY (trong suốt, hover popup) */
  .text-region {
    position: absolute;
    cursor: crosshair;
    border-radius: 2px;
    transition: background .1s;
  }
  .text-region:hover {
    background: rgba(129,140,248,.2) !important;
    outline: 1.5px solid rgba(129,140,248,.6);
  }
  .text-region[data-class="speech_bubble"]:hover { outline-color: #e84118; background: rgba(232,65,24,.15) !important; }
  .text-region[data-class="sound_effect"]:hover  { outline-color: #e67e22; background: rgba(230,126,34,.15) !important; }
  .text-region[data-class="calligraphy"]:hover   { outline-color: #8e44ad; background: rgba(142,68,173,.15) !important; }

  /* TOOLTIP */
  #tooltip {
    position: fixed; z-index: 9999; pointer-events: none; display: none;
    background: #0f1729; border: 1px solid #2d3f60; border-radius: 12px;
    padding: 14px 18px; max-width: 320px;
    box-shadow: 0 12px 40px rgba(0,0,0,.7);
    backdrop-filter: blur(12px);
    animation: tooltipIn .15s ease;
  }
  @keyframes tooltipIn { from { opacity:0; transform: translateY(4px); } to { opacity:1; transform: translateY(0); } }

  .tt-class {
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 8px; padding: 2px 8px; border-radius: 10px; display: inline-block;
  }
  .tt-class.speech_bubble { background: rgba(232,65,24,.2); color: #e84118; border: 1px solid rgba(232,65,24,.3); }
  .tt-class.sound_effect  { background: rgba(230,126,34,.2); color: #e67e22; border: 1px solid rgba(230,126,34,.3); }
  .tt-class.calligraphy   { background: rgba(142,68,173,.2); color: #8e44ad; border: 1px solid rgba(142,68,173,.3); }

  .tt-zh {
    font-size: 22px; font-weight: 700; color: #f1f5f9;
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    line-height: 1.3; margin-bottom: 4px;
  }
  .tt-pinyin {
    font-size: 13px; color: #818cf8; font-style: italic; margin-bottom: 10px;
    letter-spacing: .5px;
  }
  .tt-divider { border: none; border-top: 1px solid #1e2a45; margin: 8px 0; }
  .tt-vi-label { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }
  .tt-vi {
    font-size: 14px; color: #86efac; line-height: 1.5;
    font-weight: 500;
  }
  .tt-footer { font-size: 10px; color: #334155; margin-top: 8px; display: flex; gap: 10px; }

  /* SPINNER */
  .spinner {
    display: inline-block; width: 12px; height: 12px;
    border: 2px solid rgba(245,158,11,.3); border-top-color: #f59e0b;
    border-radius: 50%; animation: spin .8s linear infinite; margin-right: 6px;
    vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* TIPS */
  .tips {
    background: #0d1525; border: 1px solid #1e2a45; border-radius: 8px;
    padding: 12px; font-size: 12px; color: #64748b; line-height: 1.7;
  }
  .tips strong { color: #94a3b8; }
</style>
</head>
<body>

<header>
  <h1>🎌 Truyện Tranh Dịch Thuật</h1>
  <span class="badge">YOLO + PP-OCR + Tiên Hiệp Engine</span>
</header>

<div class="layout">
  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="upload-zone" style="border:none; padding:0; text-align:left;">
      <label style="font-size:12px; font-weight:bold; color:#818cf8; margin-bottom:8px; display:block;">1. Chọn ảnh truyện tranh:</label>
      <input type="file" id="fileInput" accept="image/*" style="display:block; width:100%; margin-bottom:12px; background:#1e2a45; padding:8px; border-radius:6px; color:#e2e8f0;">
    </div>

    <button class="btn btn-primary" id="processBtn" onclick="window.processPage()">
      🚀 2. Chạy Pipeline Dịch Thuật
    </button>

    <div class="status" id="statusBox">Chọn ảnh để bắt đầu...</div>

    <!-- VIEW TOGGLE -->
    <div id="viewToggleGroup" style="display:none">
      <div style="font-size:11px; color:#475569; margin-bottom:6px; font-weight:600;">XEM ẢNH:</div>
      <div class="view-toggle">
        <button class="toggle-btn" id="btnViewOrig" onclick="switchView('orig')">📖 Gốc</button>
        <button class="toggle-btn" id="btnViewInp" onclick="switchView('inp')">✨ Đã xóa chữ</button>
        <button class="toggle-btn active" id="btnViewRendered" onclick="switchView('rendered')">🇻🇳 Bản dịch</button>
      </div>
    </div>

    <!-- STATS -->
    <div class="stats-grid" id="statsGrid" style="display:none">
      <div class="stat-card"><div class="val" id="statBubbles">0</div><div class="lbl">Bong bóng</div></div>
      <div class="stat-card"><div class="val" id="statTexts">0</div><div class="lbl">Vùng chữ</div></div>
      <div class="stat-card"><div class="val" id="statInpainted">0</div><div class="lbl">Vùng đã xóa</div></div>
      <div class="stat-card"><div class="val" id="statMode" style="font-size:10px; padding-top:4px;">—</div><div class="lbl">Chế độ</div></div>
    </div>

    <div class="tips">
      <strong>💡 Cách dùng:</strong><br>
      • <strong>Rê chuột</strong> vào vùng chữ → Popup bản dịch<br>
      • Tab <strong>"Đã xóa chữ"</strong> → Xem ảnh nền sạch<br>
      • Ảnh xóa chữ tự động lưu vào <code>dataset/inpainted/</code>
    </div>
  </div>

  <!-- VIEWER -->
  <div class="viewer">
    <div id="workspace">
      <img id="main-img" src="" style="display:none" alt="Trang truyện">
      <div id="overlays"></div>
    </div>
  </div>
</div>

<!-- TOOLTIP POPUP -->
<div id="tooltip">
  <span class="tt-class" id="tt-class">💬 Bong bóng</span>
  <div class="tt-zh" id="tt-zh">—</div>
  <div class="tt-pinyin" id="tt-pinyin">—</div>
  <hr class="tt-divider">
  <div class="tt-vi-label">🇻🇳 Bản dịch tiên hiệp</div>
  <div class="tt-vi" id="tt-vi">—</div>
  <div class="tt-footer">
    <span id="tt-conf">—</span>
    <span id="tt-method">—</span>
  </div>
</div>

<script src="/static/app.js?v=3000"></script>
</body>
</html>"""


@app.get("/")
async def index():
    return HTMLResponse(content=HTML_TEMPLATE)


# ===================== HEALTH CHECK =====================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "pipeline_mode": "yolo+ocr" if pipeline.yolo_available else "ocr_fallback",
        "translator":    "4layer_xianxia",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
