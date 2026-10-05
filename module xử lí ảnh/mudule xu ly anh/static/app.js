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

    // Chuyển sang tab "Bản dịch" nếu có ảnh render
    if (window.pageData.rendered_b64) {
      window.switchView('rendered');
    } else {
      window.switchView('orig');
    }
    window.renderOverlays();

    const nBubbles = window.pageData.bubbles ? window.pageData.bubbles.length : 0;
    const nTrans   = window.pageData.bubble_translations ? window.pageData.bubble_translations.length : 0;
    document.getElementById('statBubbles').innerText   = nBubbles;
    document.getElementById('statTexts').innerText     = nTrans;
    document.getElementById('statInpainted').innerText = window.pageData.n_inpainted || 0;
    document.getElementById('statMode').innerText      = window.pageData.mode === 'yolo_segmentation+ocr' ? 'YOLO+OCR' : 'OCR Only';
    document.getElementById('statsGrid').style.display = 'grid';
    document.getElementById('viewToggleGroup').style.display = 'block';

    const inpPath = window.pageData.inpainted_path ? window.pageData.inpainted_path.split('\\').pop() : '';
    window.setStatus(
      '✅ Hoàn tất! ' + nBubbles + ' bong bóng · ' + nTrans + ' có nội dung dịch.<br>' +
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

  document.getElementById('btnViewOrig').classList.remove('active');
  document.getElementById('btnViewInp').classList.remove('active');
  if(document.getElementById('btnViewRendered'))
    document.getElementById('btnViewRendered').classList.remove('active');

  if (mode === 'orig') {
    img.src = prefix + window.pageData.image_base64;
    document.getElementById('btnViewOrig').classList.add('active');
  } else if (mode === 'rendered' && window.pageData.rendered_b64) {
    img.src = prefix + window.pageData.rendered_b64;
    if(document.getElementById('btnViewRendered'))
      document.getElementById('btnViewRendered').classList.add('active');
  } else {
    img.src = prefix + window.pageData.inpainted_b64;
    document.getElementById('btnViewInp').classList.add('active');
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

  // Dùng bubble_translations làm nguồn dữ liệu chính
  // Mỗi bubble 1 overlay duy nhất, tọa độ lấy từ YOLO bubbles[]
  const bubbleMap = {};
  if (window.pageData.bubbles) {
    window.pageData.bubbles.forEach((b, idx) => {
      bubbleMap[idx] = b;
    });
  }

  if (window.pageData.bubble_translations) {
    window.pageData.bubble_translations.forEach((bt) => {
      const bubble = bubbleMap[bt.bubble_id];
      if (!bubble) return;

      const div = document.createElement('div');
      div.className = 'text-region';
      div.dataset.class = bubble.class_name || 'speech_bubble';
      div.dataset.bid = bt.bubble_id;

      // Dùng tọa độ bbox của YOLO bubble (toàn bộ vùng bong bóng)
      div.style.left   = (bubble.x * sx) + 'px';
      div.style.top    = (bubble.y * sy) + 'px';
      div.style.width  = (bubble.w * sx) + 'px';
      div.style.height = (bubble.h * sy) + 'px';

      div.addEventListener('mouseenter', e => window.showTooltip(e, bt, bubble));
      div.addEventListener('mousemove',  window.moveTooltip);
      div.addEventListener('mouseleave', window.hideTooltip);

      container.appendChild(div);
    });
  }
};

window.showTooltip = function(e, bt, bubble) {
  const tt = document.getElementById('tooltip');
  if(!tt) return;

  const clsName = bubble.class_name || 'speech_bubble';
  const clsEl = document.getElementById('tt-class');
  clsEl.className = 'tt-class ' + clsName;
  clsEl.innerText = window.CLASS_LABELS[clsName] || clsName;

  document.getElementById('tt-zh').innerText     = bt.text_zh || '—';
  document.getElementById('tt-pinyin').innerText = bt.pinyin  || '—';
  document.getElementById('tt-vi').innerText     = bt.vi      || '—';
  document.getElementById('tt-conf').innerText   = 'YOLO: ' + ((bubble.confidence || 0) * 100).toFixed(1) + '%';
  document.getElementById('tt-method').innerText = clsName === 'calligraphy' ? '✍️ Thư pháp' :
    clsName === 'sound_effect' ? '💥 SFX' : '4 lớp tiên hiệp';

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
  const fInput = document.getElementById('fileInput');
  if (fInput) {
    fInput.addEventListener('change', function() {
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
  }

  window.addEventListener('dragover', e => e.preventDefault());
  window.addEventListener('drop', e => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      if (fInput) {
        fInput.files = e.dataTransfer.files;
        fInput.dispatchEvent(new Event('change'));
      }
    }
  });

  window.addEventListener('resize', () => { if (window.pageData) window.renderOverlays(); });
});
