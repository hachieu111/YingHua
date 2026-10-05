
let pageData = null;
let viewMode = 'orig';   // 'orig' or 'inp'
const CLASS_LABELS = {
  'speech_bubble': '💬 Bong bóng chat',
  'sound_effect':  '💥 Âm thanh / SFX',
  'calligraphy':   '✍️ Thư pháp',
  'floating_text': '🌊 Chữ trôi nổi',
};

function setStatus(msg, type='') {
  const el = document.getElementById('statusBox');
  el.className = 'status ' + type;
  el.innerHTML = msg;
}

// ===================== UPLOAD PREVIEW =====================
document.getElementById('fileInput').addEventListener('change', function() {
  if (!this.files.length) return;
  const url = URL.createObjectURL(this.files[0]);
  const img = document.getElementById('main-img');
  img.src = url;
  img.style.display = 'block';
  document.getElementById('overlays').innerHTML = '';
  document.getElementById('statsGrid').style.display = 'none';
  document.getElementById('viewToggleGroup').style.display = 'none';
  setStatus('✅ Đã chọn: <b>' + this.files[0].name + '</b><br>Đang tự động chạy pipeline...');
  pageData = null;
  
  // Tự động chạy luôn không cần bấm nút
  processPage();
});

// Drag & Drop
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => {
  e.preventDefault();
  if (e.dataTransfer.files && e.dataTransfer.files.length) {
    document.getElementById('fileInput').files = e.dataTransfer.files;
    document.getElementById('fileInput').dispatchEvent(new Event('change'));
  }
});

// ===================== PROCESS =====================
async function processPage() {
  const fileInput = document.getElementById('fileInput');
  if (!fileInput.files.length) { setStatus('⚠️ Vui lòng chọn ảnh trước!', 'error'); return; }

  const btn = document.getElementById('processBtn');
  btn.disabled = true;
  setStatus('<span class="spinner"></span>Đang chạy YOLO → PP-OCR → Dịch → Inpainting...', 'loading');
  document.getElementById('overlays').innerHTML = '';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const res = await fetch('/process-page', { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({detail: 'Server lỗi ' + res.status}));
      throw new Error(err.detail || 'Server lỗi ' + res.status);
    }
    pageData = await res.json();

    // Hiển thị ảnh gốc mặc định
    switchView('orig');

    // Render overlays
    renderOverlays();

    // Stats
    document.getElementById('statBubbles').innerText = pageData.bubbles.length;
    document.getElementById('statTexts').innerText   = pageData.texts.length;
    document.getElementById('statInpainted').innerText = pageData.n_inpainted;
    document.getElementById('statMode').innerText    = pageData.mode === 'yolo_segmentation+ocr' ? 'YOLO+OCR' : 'OCR Only';
    document.getElementById('statsGrid').style.display = 'grid';
    document.getElementById('viewToggleGroup').style.display = 'block';

    const inpPath = pageData.inpainted_path ? pageData.inpainted_path.split('\\').pop() : '';
    setStatus(
      '✅ Hoàn tất! ' + pageData.texts.length + ' vùng chữ được nhận diện & dịch.<br>' +
      (inpPath ? '📁 Ảnh sạch lưu tại: <code>' + inpPath + '</code>' : ''),
      'success'
    );

  } catch(e) {
    setStatus('❌ Lỗi: ' + e.message, 'error');
    console.error(e);
  } finally {
    btn.disabled = false;
  }
}

// ===================== VIEW TOGGLE =====================
function switchView(mode) {
  viewMode = mode;
  if (!pageData) return;

  const img = document.getElementById('main-img');
  const prefix = 'data:image/jpeg;base64,';

  if (mode === 'orig') {
    img.src = prefix + pageData.image_base64;
    document.getElementById('btnViewOrig').classList.add('active');
    document.getElementById('btnViewInp').classList.remove('active');
  } else {
    img.src = prefix + pageData.inpainted_b64;
    document.getElementById('btnViewInp').classList.add('active');
    document.getElementById('btnViewOrig').classList.remove('active');
  }
  img.style.display = 'block';
  img.onload = renderOverlays;
}

// ===================== RENDER OVERLAYS =====================
function renderOverlays() {
  if (!pageData) return;
  const container = document.getElementById('overlays');
  container.innerHTML = '';

  const img = document.getElementById('main-img');
  const sx = img.clientWidth  / pageData.width;
  const sy = img.clientHeight / pageData.height;

  // Group by bubble_id → dùng bản dịch đầy đủ của bubble
  const bubbleCache = {};
  pageData.bubble_translations.forEach(bt => {
    bubbleCache[bt.bubble_id] = bt;
  });

  pageData.texts.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = 'text-region';
    div.dataset.class = item.class_name || 'speech_bubble';
    div.dataset.idx = idx;

    div.style.left   = (item.x * sx) + 'px';
    div.style.top    = (item.y * sy) + 'px';
    div.style.width  = (item.w * sx) + 'px';
    div.style.height = (item.h * sy) + 'px';

    // Hover events → Tooltip
    div.addEventListener('mouseenter', e => showTooltip(e, item, bubbleCache));
    div.addEventListener('mousemove',  moveTooltip);
    div.addEventListener('mouseleave', hideTooltip);

    container.appendChild(div);
  });
}

// ===================== TOOLTIP =====================
function showTooltip(e, item, bubbleCache) {
  const tt = document.getElementById('tooltip');
  const bid = item.bubble_id;
  const bData = bubbleCache[bid] || {};

  // Class badge
  const clsEl = document.getElementById('tt-class');
  clsEl.className = 'tt-class ' + (item.class_name || 'speech_bubble');
  clsEl.innerText = CLASS_LABELS[item.class_name] || item.class_name;

  // Ưu tiên hiển thị chữ + dịch của toàn bộ bubble (full câu)
  document.getElementById('tt-zh').innerText    = bData.text_zh   || item.text_zh   || item.full_zh || '—';
  document.getElementById('tt-pinyin').innerText = bData.pinyin   || item.pinyin    || '—';
  document.getElementById('tt-vi').innerText    = bData.vi        || item.vi        || '—';
  document.getElementById('tt-conf').innerText  = 'OCR: ' + ((item.confidence || 0) * 100).toFixed(1) + '%';
  document.getElementById('tt-method').innerText = item.class_name === 'calligraphy' ? '✍️ Thư pháp' :
    item.class_name === 'sound_effect' ? '💥 SFX' : '4 lớp tiên hiệp';

  tt.style.display = 'block';
  moveTooltip(e);
}

function moveTooltip(e) {
  const tt = document.getElementById('tooltip');
  const margin = 14;
  let left = e.clientX + margin;
  let top  = e.clientY + margin;
  if (left + 340 > window.innerWidth)  left = e.clientX - 340 - margin;
  if (top  + 200 > window.innerHeight) top  = e.clientY - 200 - margin;
  tt.style.left = left + 'px';
  tt.style.top  = top  + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

// Re-render khi resize
window.addEventListener('resize', () => { if (pageData) renderOverlays(); });
