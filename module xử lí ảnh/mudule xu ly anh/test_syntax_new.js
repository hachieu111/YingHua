
window.pageData = null;
window.viewMode = 'orig';

window.CLASS_LABELS = {
  'speech_bubble': '💬 Bong bóng chat',
  'sound_effect':  '💥 Âm thanh / SFX',
  'calligraphy':   '✍️ Thư pháp',
  'floating_text': '🌊 Chữ trôi nổi',
};

window.setStatus = function(msg, type='') {
  const el = document.getElementById('statusBox');
  if(el) {
    el.className = 'status ' + type;
    el.innerHTML = msg;
  }
};

window.processPage = async function() {
  const fileInput = document.getElementById('fileInput');
  if (!fileInput || !fileInput.files || !fileInput.files.length) { 
    window.setStatus('⚠️ Vui lòng chọn ảnh trước!', 'error'); 
    return; 
  }

  const btn = document.getElementById('processBtn');
  if(btn) btn.disabled = true;
  window.setStatus('<span class="spinner"></span>Đang chạy YOLO → PP-OCR → Dịch → Inpainting...', 'loading');
  document.getElementById('overlays').innerHTML = '';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const res = await fetch('/process-page', { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({detail: 'Server lỗi ' + res.status}));
      throw new Error(err.detail || 'Server lỗi ' + res.status);
    }
    window.pageData = await res.json();

    window.switchView('orig');
    window.renderOverlays();

    document.getElementById('statBubbles').innerText = window.pageData.bubbles ? window.pageData.bubbles.length : 0;
    document.getElementById('statTexts').innerText   = window.pageData.texts ? window.pageData.texts.length : 0;
    document.getElementById('statInpainted').innerText = window.pageData.n_inpainted || 0;
    document.getElementById('statMode').innerText    = window.pageData.mode === 'yolo_segmentation+ocr' ? 'YOLO+OCR' : 'OCR Only';
    document.getElementById('statsGrid').style.display = 'grid';
    document.getElementById('viewToggleGroup').style.display = 'block';

    const inpPath = window.pageData.inpainted_path ? window.pageData.inpainted_path.split('\\').pop() : '';
    window.setStatus(
      '✅ Hoàn tất! ' + (window.pageData.texts ? window.pageData.texts.length : 0) + ' vùng chữ được nhận diện & dịch.<br>' +
      (inpPath ? '📁 Ảnh sạch lưu tại: <code>' + inpPath + '</code>' : ''),
      'success'
    );

  } catch(e) {
    window.setStatus('❌ Lỗi: ' + e.message, 'error');
    console.error(e);
  } finally {
    if(btn) btn.disabled = false;
  }
};

window.switchView = function(mode) {
  window.viewMode = mode;
  if (!window.pageData) return;

  const img = document.getElementById('main-img');
  if(!img) return;
  const prefix = 'data:image/jpeg;base64,';

  if (mode === 'orig') {
    img.src = prefix + window.pageData.image_base64;
    document.getElementById('btnViewOrig').classList.add('active');
    document.getElementById('btnViewInp').classList.remove('active');
  } else {
    img.src = prefix + window.pageData.inpainted_b64;
    document.getElementById('btnViewInp').classList.add('active');
    document.getElementById('btnViewOrig').classList.remove('active');
  }
  img.style.display = 'block';
  img.onload = window.renderOverlays;
};

window.renderOverlays = function() {
  if (!window.pageData) return;
  const container = document.getElementById('overlays');
  if(!container) return;
  container.innerHTML = '';

  const img = document.getElementById('main-img');
  if(!img) return;
  const sx = img.clientWidth  / window.pageData.width;
  const sy = img.clientHeight / window.pageData.height;

  const bubbleCache = {};
  if(window.pageData.bubble_translations) {
    window.pageData.bubble_translations.forEach(bt => {
      bubbleCache[bt.bubble_id] = bt;
    });
  }

  if(window.pageData.texts) {
    window.pageData.texts.forEach((item, idx) => {
      const div = document.createElement('div');
      div.className = 'text-region';
      div.dataset.class = item.class_name || 'speech_bubble';
      div.dataset.idx = idx;

      div.style.left   = (item.x * sx) + 'px';
      div.style.top    = (item.y * sy) + 'px';
      div.style.width  = (item.w * sx) + 'px';
      div.style.height = (item.h * sy) + 'px';

      div.addEventListener('mouseenter', e => window.showTooltip(e, item, bubbleCache));
      div.addEventListener('mousemove',  window.moveTooltip);
      div.addEventListener('mouseleave', window.hideTooltip);

      container.appendChild(div);
    });
  }
};

window.showTooltip = function(e, item, bubbleCache) {
  const tt = document.getElementById('tooltip');
  if(!tt) return;
  const bid = item.bubble_id;
  const bData = bubbleCache[bid] || {};

  const clsEl = document.getElementById('tt-class');
  clsEl.className = 'tt-class ' + (item.class_name || 'speech_bubble');
  clsEl.innerText = window.CLASS_LABELS[item.class_name] || item.class_name;

  document.getElementById('tt-zh').innerText    = bData.text_zh   || item.text_zh   || item.full_zh || '—';
  document.getElementById('tt-pinyin').innerText = bData.pinyin   || item.pinyin    || '—';
  document.getElementById('tt-vi').innerText    = bData.vi        || item.vi        || '—';
  document.getElementById('tt-conf').innerText  = 'OCR: ' + ((item.confidence || 0) * 100).toFixed(1) + '%';
  document.getElementById('tt-method').innerText = item.class_name === 'calligraphy' ? '✍️ Thư pháp' :
    item.class_name === 'sound_effect' ? '💥 SFX' : '4 lớp tiên hiệp';

  tt.style.display = 'block';
  window.moveTooltip(e);
};

window.moveTooltip = function(e) {
  const tt = document.getElementById('tooltip');
  if(!tt) return;
  const margin = 14;
  let left = e.clientX + margin;
  let top  = e.clientY + margin;
  if (left + 340 > window.innerWidth)  left = e.clientX - 340 - margin;
  if (top  + 200 > window.innerHeight) top  = e.clientY - 200 - margin;
  tt.style.left = left + 'px';
  tt.style.top  = top  + 'px';
};

window.hideTooltip = function() {
  const tt = document.getElementById('tooltip');
  if(tt) tt.style.display = 'none';
};

document.addEventListener("DOMContentLoaded", function() {
  document.getElementById('fileInput').addEventListener('change', function() {
    if (!this.files || !this.files.length) return;
    const url = URL.createObjectURL(this.files[0]);
    const img = document.getElementById('main-img');
    img.src = url;
    img.style.display = 'block';
    document.getElementById('overlays').innerHTML = '';
    document.getElementById('statsGrid').style.display = 'none';
    document.getElementById('viewToggleGroup').style.display = 'none';
    window.setStatus('✅ Đã chọn: <b>' + this.files[0].name + '</b><br>Đang tự động chạy pipeline...');
    window.pageData = null;
    
    window.processPage();
  });

  window.addEventListener('dragover', e => e.preventDefault());
  window.addEventListener('drop', e => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      document.getElementById('fileInput').files = e.dataTransfer.files;
      document.getElementById('fileInput').dispatchEvent(new Event('change'));
    }
  });

  window.addEventListener('resize', () => { if (window.pageData) window.renderOverlays(); });
});
