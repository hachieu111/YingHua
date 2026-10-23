'use strict';
/* Trình đọc: chế độ Đọc (ảnh đã dịch) và Học (ảnh gốc + lớp chữ bôi đen được + popup bong bóng). */

YH.readerMode = null;
YH.chapterCache = null;

function polygonPoints(b) {
  const p = b.polygon;
  let pts = null;
  if (Array.isArray(p) && p.length >= 3) {
    if (Array.isArray(p[0])) pts = p.map((q) => q[0] + ',' + q[1]);
    else if (typeof p[0] === 'number' && p.length % 2 === 0) { pts = []; for (let i = 0; i < p.length; i += 2) pts.push(p[i] + ',' + p[i + 1]); }
    else if (typeof p[0] === 'object' && p[0] && 'x' in p[0]) pts = p.map((q) => q.x + ',' + q.y);
  }
  if (!pts) pts = [[b.x, b.y], [b.x + b.w, b.y], [b.x + b.w, b.y + b.h], [b.x, b.y + b.h]].map((q) => q.join(','));
  return pts.join(' ');
}

YH.pages.read = async (ctx) => {
  const { root } = ctx, pid = ctx.args[0];
  const hovered = new Set();
  let page = await safe(api('/api/pages/' + pid));
  if (!ctx.alive()) return;
  if (!page) return root.appendChild(h('p', { class: 'error' }, 'Không tải được trang.'));
  let chapter = YH.chapterCache && YH.chapterCache.id === page.chapter_id && YH.chapterCache.data.pages.some((p) => p.id === page.id) ? YH.chapterCache.data : null;
  if (!chapter) {
    chapter = await safe(api('/api/chapters/' + page.chapter_id));
    if (!ctx.alive()) return;
    if (chapter) YH.chapterCache = { id: page.chapter_id, data: chapter };
  }
  const me = chapter && chapter.pages.find((p) => p.id === page.id);
  const pageNo = (me && me.page_no) || page.page_no;
  const total = chapter ? chapter.pages.length : '?';
  if (!YH.readerMode) YH.readerMode = (chapter && chapter.progress && chapter.progress.mode) || (YH.settings && YH.settings.default_mode) || 'read';
  let mode = YH.readerMode;
  let sideTab = 'lookup';

  /* ---------- khung ---------- */
  const stageWrap = h('div', { class: 'stage-wrap' });
  const side = h('aside', { class: 'reader-side' });
  const sideBody = h('div', { class: 'side-body' });
  const lookupHolder = h('div', {}, h('p', { class: 'muted' }, 'Chế độ Học: bôi đen chữ Hán trên ảnh để tra từ.'));
  const sugHolder = h('div');
  const modeBtns = h('div', { class: 'seg' });
  const goto = (id) => { if (id) location.hash = '#/read/' + id; };

  const saveProgress = () => {
    api(`/api/chapters/${page.chapter_id}/progress`, { method: 'PUT', body: { last_page_no: pageNo, mode, completed: !page.next_page_id }, silent: true }).catch(() => {});
  };
  const setMode = (m) => { mode = YH.readerMode = m; drawModes(); renderStage(); saveProgress(); };
  const drawModes = () => modeBtns.replaceChildren(
    h('button', { class: 'btn small' + (mode === 'read' ? ' primary' : ''), onclick: () => setMode('read') }, 'Đọc'),
    h('button', { class: 'btn small' + (mode === 'learn' ? ' primary' : ''), onclick: () => setMode('learn') }, 'Học'));

  async function download(variant) {
    const r = await api(`/api/pages/${pid}/image/${variant}`, { query: { download: true }, raw: true });
    if (!r.ok) { let d = r.statusText; try { d = fmtDetail((await r.json()).detail); } catch (e) { /* */ } return toast(d, 'error'); }
    const blob = await r.blob();
    const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(r.headers.get('content-disposition') || '');
    const a = h('a', { href: URL.createObjectURL(blob), download: m ? decodeURIComponent(m[1]) : `trang${pageNo}-${variant}.png` });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  const t = page.translation;
  const bar = h('div', { class: 'reader-bar' },
    chapter ? h('a', { href: '#/chapter/' + page.chapter_id, title: 'Về chương' }, `← ${chapter.series.title_vi} · Ch.${fmtNum(chapter.number)}`) : h('a', { href: '#/library' }, '← Thư viện'),
    h('span', { class: 'spacer' }),
    h('button', { class: 'btn small', disabled: !page.prev_page_id, onclick: () => goto(page.prev_page_id) }, '← Trước'),
    h('b', {}, `Trang ${pageNo}/${total}`),
    h('button', { class: 'btn small', disabled: !page.next_page_id, onclick: () => goto(page.next_page_id) }, 'Sau →'),
    modeBtns,
    t ? statusBadge(t.status) : statusBadge('missing'));

  const sideTabs = h('div');
  const drawSide = () => {
    sideTabs.replaceChildren(tabs([['lookup', 'Tra từ'], ['sug', 'Gợi ý từ vựng']], sideTab, (k) => { sideTab = k; drawSide(); if (k === 'sug') loadSug(); }));
    lookupHolder.style.display = sideTab === 'lookup' ? '' : 'none';
    sugHolder.style.display = sideTab === 'sug' ? '' : 'none';
  };
  sideBody.append(lookupHolder, sugHolder);
  side.append(sideTabs, sideBody);

  /* ---------- gợi ý ---------- */
  async function loadSug() {
    clear(sugHolder).appendChild(h('p', { class: 'muted' }, 'Đang tính gợi ý…'));
    const items = await safe(api(`/api/chapters/${page.chapter_id}/suggestions`));
    if (!ctx.alive() || !items) return;
    clear(sugHolder);
    sugHolder.appendChild(h('div', { class: 'row' }, h('b', {}, 'Gợi ý cho chương'), h('button', { class: 'btn small', onclick: loadSug }, '↻')));
    const active = items.filter((s) => s.status !== 'accepted' && s.status !== 'dismissed');
    if (!active.length) sugHolder.appendChild(h('p', { class: 'muted' }, 'Không có gợi ý (hãy dịch xong trang rồi thử lại).'));
    active.forEach((s) => {
      const row = h('div', { class: 'sug' },
        h('div', {}, h('a', { href: '#', class: 'zh big', onclick: (e) => { e.preventDefault(); showLookup(s.term, null); } }, s.term), ' ', h('small', {}, s.pinyin || ''), ' ', ttsBtn(s.term)),
        h('div', {}, s.meaning || h('span', { class: 'muted' }, '—')),
        h('small', { class: 'muted' }, [s.reason, s.occurrences != null ? `xuất hiện ${s.occurrences} lần` : null, s.score != null ? 'điểm ' + Number(s.score).toFixed(2) : null].filter(Boolean).join(' · ')),
        h('div', { class: 'row' },
          h('button', { class: 'btn small primary', onclick: async () => { if (await safe(api(`/api/suggestions/${s.id}/accept`, { method: 'POST' }))) { toast('Đã thêm vào sổ tay', 'ok'); row.remove(); } } }, '✔ Thêm'),
          h('button', { class: 'btn small', onclick: async () => { if (await ok(api(`/api/suggestions/${s.id}/dismiss`, { method: 'POST' }))) row.remove(); } }, '✖ Bỏ qua')));
      sugHolder.appendChild(row);
    });
  }

  function showLookup(term, bubbleId) {
    sideTab = 'lookup'; drawSide();
    clear(lookupHolder).appendChild(lookupBox(term, { bubbleId, source: bubbleId ? 'highlight' : 'lookup' }));
  }

  /* ---------- stage ---------- */
  let learnCleanup = null;
  function renderStage() {
    if (learnCleanup) { learnCleanup(); learnCleanup = null; }
    clear(stageWrap);
    if (mode === 'read') return renderRead();
    return renderLearn();
  }

  function statusBlock() {
    const tr = page.translation;
    const box = h('div', { class: 'card status-block' }, h('div', {}, 'Trạng thái dịch: ', statusBadge(tr ? tr.status : 'missing')));
    if (tr && tr.error) box.appendChild(h('pre', { class: 'error small' }, tr.error));
    if (tr && (tr.status === 'queued' || tr.status === 'running')) box.appendChild(h('p', { class: 'muted' }, '⟳ Đang chờ xử lý, trang sẽ tự cập nhật…'));
    if (chapter && chapter.can_edit && (!tr || tr.status === 'failed')) {
      box.appendChild(h('button', { class: 'btn', onclick: async () => { if (await safe(api(`/api/pages/${pid}/retranslate`, { method: 'POST' }))) { toast('Đã đưa vào hàng đợi', 'ok'); reload(); } } }, '↻ Dịch lại'));
    }
    return box;
  }

  function renderRead() {
    stageWrap.appendChild(h('div', { class: 'row' }, h('button', { class: 'btn small', disabled: !page.has_rendered, onclick: () => download('rendered') }, '⬇ Tải xuống')));
    if (page.has_rendered) {
      stageWrap.appendChild(h('div', { class: 'stage' }, mediaImg(page.images.rendered, { class: 'page-img', alt: 'Trang đã dịch' })));
    } else stageWrap.appendChild(statusBlock());
  }

  function renderLearn() {
    stageWrap.appendChild(h('div', { class: 'row' }, h('button', { class: 'btn small', disabled: !page.has_original, onclick: () => download('original') }, '⬇ Tải ảnh gốc'),
      h('small', { class: 'muted' }, 'Rê chuột vào bong bóng để xem bản dịch · bôi đen chữ Hán để tra từ')));
    if (!page.has_original) return stageWrap.appendChild(h('p', { class: 'error' }, 'Ảnh gốc đã hết hạn lưu trữ.'));
    if (!page.bubbles.length) stageWrap.appendChild(statusBlock());

    const stage = h('div', { class: 'stage learn' });
    const img = mediaImg(page.images.original, { class: 'page-img', draggable: 'false' });
    const overlay = h('div', { class: 'overlay' });
    const popup = h('div', { class: 'bubble-popup', style: { display: 'none' } });
    stage.append(img, overlay, popup);
    stageWrap.appendChild(stage);

    let activeId = null, hideTimer = null, pinned = false;
    const byId = new Map(page.bubbles.map((b) => [b.id, b]));
    const polys = new Map();

    function layout() {
      const nw = img.naturalWidth;
      if (!nw) return;
      overlay.style.transform = `scale(${img.clientWidth / nw})`;
    }
    function build() {
      const nw = img.naturalWidth, nh = img.naturalHeight;
      overlay.style.width = nw + 'px'; overlay.style.height = nh + 'px';
      const svg = svgEl('svg', { viewBox: `0 0 ${nw} ${nh}`, width: nw, height: nh, class: 'polys' });
      const tl = h('div', { class: 'textlayer' });
      page.bubbles.forEach((b) => {
        const pg = svgEl('polygon', { points: polygonPoints(b), class: 'bpoly', 'data-bubble': b.id });
        svg.appendChild(pg); polys.set(b.id, pg);
        (b.lines || []).forEach((l) => {
          if (!l || !l.text) return;
          const span = h('span', { class: 'tl' + (l.vertical ? ' v' : ''), dataset: { bubble: b.id } }, l.text);
          span.style.left = l.x + 'px'; span.style.top = l.y + 'px';
          if (l.vertical) { span.style.fontSize = l.w + 'px'; span.style.lineHeight = l.w + 'px'; span.style.width = l.w + 'px'; }
          else { span.style.fontSize = l.h + 'px'; span.style.lineHeight = l.h + 'px'; span.style.height = l.h + 'px'; }
          span._l = l;
          tl.appendChild(span);
        });
      });
      overlay.append(svg, tl);
      layout();
      requestAnimationFrame(() => {
        tl.querySelectorAll('.tl').forEach((span) => {
          const l = span._l;
          if (l.vertical) { const n = span.scrollHeight || span.offsetHeight; if (n && l.h) span.style.transform = `scaleY(${l.h / n})`; }
          else { const n = span.scrollWidth || span.offsetWidth; if (n && l.w) span.style.transform = `scaleX(${l.w / n})`; }
        });
      });
    }
    if (img.complete && img.naturalWidth) build(); else img.addEventListener('load', build, { once: true });
    const ro = new ResizeObserver(layout);
    ro.observe(img);

    /* popup bong bóng */
    const hide = () => { if (pinned) return; popup.style.display = 'none'; if (activeId != null && polys.get(activeId)) polys.get(activeId).classList.remove('on'); activeId = null; };
    const scheduleHide = () => { clearTimeout(hideTimer); hideTimer = setTimeout(hide, 300); };
    function placePopup(b) {
      const k = img.clientWidth / img.naturalWidth;
      popup.style.display = 'block';
      const pw = popup.offsetWidth, ph = popup.offsetHeight;
      let left = Math.min(Math.max(0, b.x * k), Math.max(0, stage.clientWidth - pw));
      let top = (b.y + b.h) * k + 6;
      if (top + ph > stage.clientHeight && b.y * k - ph - 6 >= 0) top = b.y * k - ph - 6;
      popup.style.left = left + 'px'; popup.style.top = Math.max(0, top) + 'px';
    }
    function popupContent(b, editing) {
      const c = h('div', {});
      c.appendChild(h('div', { class: 'zh pz' }, b.text_zh));
      c.appendChild(h('div', { class: 'py' }, b.pinyin || ''));
      if (!editing) {
        c.appendChild(h('div', { class: 'vi' }, b.text_vi || h('i', { class: 'muted' }, '(chưa có bản dịch)'), b.edited ? h('span', { class: 'badge edited', title: 'Bản dịch bạn đã sửa' }, 'đã sửa') : null));
        c.appendChild(h('div', { class: 'row' },
          ttsBtn(b.text_zh, b.id),
          h('button', { class: 'btn small', title: 'Sửa bản dịch', onclick: () => { pinned = true; fill(b, true); } }, '✏️ Sửa'),
          b.edited ? h('button', { class: 'btn small', title: 'Khôi phục bản dịch gốc', onclick: async () => {
            if (await ok(api(`/api/bubbles/${b.id}/edit`, { method: 'DELETE' }))) { b.text_vi = b.text_vi_original; b.edited = false; toast('Đã khôi phục', 'ok'); fill(b); }
          } }, '↩ Gốc') : null));
      } else {
        const ta = h('textarea', { rows: 3, value: b.text_vi || '' });
        c.appendChild(ta);
        c.appendChild(h('div', { class: 'row' },
          h('button', { class: 'btn small primary', onclick: async () => {
            const v = ta.value.trim();
            if (!v) return toast('Không được để trống', 'error');
            const r = await safe(api(`/api/bubbles/${b.id}/edit`, { method: 'PUT', body: { text_vi: v } }));
            if (r) { b.text_vi = r.text_vi; b.edited = true; pinned = false; toast('Đã lưu bản dịch của bạn', 'ok'); fill(b); }
          } }, 'Lưu'),
          h('button', { class: 'btn small', onclick: () => { pinned = false; fill(b); } }, 'Huỷ')));
        setTimeout(() => ta.focus(), 0);
      }
      return c;
    }
    function fill(b, editing) { clear(popup).appendChild(popupContent(b, editing)); placePopup(b); }
    function show(id) {
      clearTimeout(hideTimer);
      if (pinned || id === activeId) return;
      if (activeId != null && polys.get(activeId)) polys.get(activeId).classList.remove('on');
      activeId = id;
      const b = byId.get(id);
      if (!b) return;
      polys.get(id) && polys.get(id).classList.add('on');
      fill(b);
      if (!hovered.has(id) && b.text_zh) {
        setTimeout(() => {
          if (activeId === id && !hovered.has(id)) {
            hovered.add(id);
            api('/api/dict/events', { method: 'POST', body: { term: b.text_zh.slice(0, 32), action: 'hover', bubble_id: id }, silent: true }).catch(() => {});
          }
        }, 600);
      }
    }
    overlay.addEventListener('mouseover', (e) => { const el = e.target.closest && e.target.closest('[data-bubble]'); if (el) show(Number(el.dataset.bubble)); });
    overlay.addEventListener('mouseout', (e) => { if (e.relatedTarget && popup.contains(e.relatedTarget)) return; scheduleHide(); });
    popup.addEventListener('mouseenter', () => clearTimeout(hideTimer));
    popup.addEventListener('mouseleave', scheduleHide);

    /* bôi đen -> tra từ */
    stage.addEventListener('mouseup', () => setTimeout(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) return;
      const txt = sel.toString().replace(/\s+/g, '');
      if (!txt) return;
      const n = sel.anchorNode;
      const el = n && (n.nodeType === 1 ? n : n.parentElement);
      const span = el && el.closest && el.closest('.tl');
      if (!span || !overlay.contains(span)) return;
      const bid = Number(span.dataset.bubble);
      const b = byId.get(bid);
      const term = Array.from(txt).slice(0, 32).join('');
      showLookup(term, b && b.text_zh && b.text_zh.includes(term) ? bid : null);
    }, 0));

    learnCleanup = () => { ro.disconnect(); clearTimeout(hideTimer); };
  }

  /* ---------- poll khi đang dịch ---------- */
  async function reload() {
    const np = await safe(api('/api/pages/' + pid));
    if (!ctx.alive() || !np) return;
    page = np;
    renderStage();
  }
  if (t && (t.status === 'queued' || t.status === 'running')) {
    const iv = setInterval(async () => {
      const np = await api('/api/pages/' + pid, { silent: true }).catch(() => null);
      if (np && np.translation && np.translation.status !== 'queued' && np.translation.status !== 'running') { clearInterval(iv); if (ctx.alive()) { page = np; bar.querySelector('.badge').replaceWith(statusBadge(np.translation.status)); renderStage(); } }
    }, 3000);
    ctx.onCleanup(() => clearInterval(iv));
  }

  /* ---------- phím tắt ---------- */
  const onKey = (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const tag = (e.target.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag) || e.target.isContentEditable) return;
    if (document.querySelector('.modal-back')) return;
    if (e.key === ' ') { e.preventDefault(); setMode(mode === 'read' ? 'learn' : 'read'); }
    else if (e.key === 'ArrowLeft') goto(page.prev_page_id);
    else if (e.key === 'ArrowRight') goto(page.next_page_id);
  };
  document.addEventListener('keydown', onKey);
  ctx.onCleanup(() => document.removeEventListener('keydown', onKey));

  root.appendChild(h('div', { class: 'reader' }, bar, h('div', { class: 'reader-main' }, stageWrap, side)));
  drawModes(); drawSide(); renderStage(); saveProgress();
};
