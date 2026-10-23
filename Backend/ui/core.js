'use strict';
/* Lõi: DOM helper, api() có tự refresh token, media blob, TTS, toast, modal, từ điển dùng chung. */
const YH = { user: null, settings: null, media: new Map(), pages: {}, token: 0, cleanups: [] };

/* ---------- DOM ---------- */
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (['value', 'checked', 'disabled', 'selected', 'textContent', 'innerHTML'].includes(k)) el[k] = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  const add = (c) => {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(add);
    else el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  };
  kids.forEach(add);
  return el;
}
const $ = (s, r = document) => r.querySelector(s);
const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };
const fmtDate = (s) => (s ? new Date(s).toLocaleString('vi-VN') : '');
const fmtNum = (n) => (n == null ? '' : String(parseFloat(n)));

/* ---------- toast ---------- */
function toast(msg, kind = 'info') {
  let box = $('#toasts');
  if (!box) { box = h('div', { id: 'toasts' }); document.body.appendChild(box); }
  const t = h('div', { class: 'toast ' + kind }, msg);
  box.appendChild(t);
  setTimeout(() => t.remove(), kind === 'error' ? 6000 : 3000);
}

/* ---------- token ---------- */
const getAccess = () => localStorage.getItem('yh_access');
const getRefresh = () => localStorage.getItem('yh_refresh');
function setTokens(a, r) { localStorage.setItem('yh_access', a); localStorage.setItem('yh_refresh', r); }
function clearTokens() { localStorage.removeItem('yh_access'); localStorage.removeItem('yh_refresh'); }

class ApiError extends Error {
  constructor(status, detail) { super(detail); this.status = status; this.detail = detail; }
}
function fmtDetail(d) {
  if (d == null) return 'Lỗi không xác định';
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => (e.loc ? e.loc.slice(1).join('.') + ': ' : '') + (e.msg || JSON.stringify(e))).join('; ');
  return JSON.stringify(d);
}

let refreshing = null;
function doRefresh() {
  if (!refreshing) {
    refreshing = (async () => {
      const rt = getRefresh();
      if (!rt) throw new Error('no refresh token');
      const r = await fetch('/api/auth/refresh', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }),
      });
      if (!r.ok) throw new Error('refresh failed');
      const d = await r.json();
      setTokens(d.access_token, d.refresh_token);
    })().finally(() => { refreshing = null; });
  }
  return refreshing;
}

function buildUrl(path, query) {
  if (!query) return path;
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== '') u.append(k, v);
  const s = u.toString();
  return s ? path + (path.includes('?') ? '&' : '?') + s : path;
}
function rawFetch(path, opts, token) {
  const headers = { ...(opts.headers || {}) };
  if (token) headers.Authorization = 'Bearer ' + token;
  let body = opts.body;
  if (body !== undefined && !(body instanceof FormData) && typeof body !== 'string') {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  return fetch(buildUrl(path, opts.query), { method: opts.method || 'GET', headers, body });
}

/** Gọi API. opts: method, query, body(object|FormData|string), blob, raw (trả Response, không throw), silent. */
async function api(path, opts = {}) {
  const authPath = /^\/api\/auth\/(login|register|refresh)/.test(path);
  const used = getAccess();
  let r = await rawFetch(path, opts, authPath ? null : used);
  if (r.status === 401 && !authPath && getRefresh()) {
    try {
      if (getAccess() === used) await doRefresh(); // token đã đổi bởi request khác -> chỉ cần thử lại
      r = await rawFetch(path, opts, getAccess());
    } catch (e) {
      logoutLocal();
      const err = new ApiError(401, 'Phiên đăng nhập đã hết hạn, hãy đăng nhập lại');
      if (!opts.silent) toast(err.detail, 'error');
      throw err;
    }
  }
  if (opts.raw) return r;
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = fmtDetail((await r.json()).detail); } catch (e) { /* không phải JSON */ }
    const err = new ApiError(r.status, detail);
    if (!opts.silent) toast(`${r.status}: ${detail}`, 'error');
    throw err;
  }
  if (opts.blob) return r.blob();
  if (r.status === 204) return null;
  const ct = r.headers.get('content-type') || '';
  return ct.includes('json') ? r.json() : r.text();
}
const safe = (p) => p.catch(() => null); // bỏ qua lỗi (đã toast)
const ok = (p) => p.then(() => true, () => false); // cho API trả 204

/* ---------- media (ảnh/audio cần Authorization) ---------- */
function media(url) {
  if (!YH.media.has(url)) {
    const p = api(url, { blob: true, silent: true }).then((b) => URL.createObjectURL(b));
    p.catch(() => YH.media.delete(url));
    YH.media.set(url, p);
  }
  return YH.media.get(url);
}
function clearMedia() {
  for (const p of YH.media.values()) p.then((u) => URL.revokeObjectURL(u)).catch(() => {});
  YH.media.clear();
}
function mediaImg(url, props) {
  const img = h('img', props);
  media(url).then((u) => { img.src = u; }).catch((e) => { img.alt = 'Không tải được ảnh'; img.title = e.detail || ''; img.classList.add('broken'); });
  return img;
}

/* ---------- TTS ---------- */
let curAudio = null;
async function speak(text, bubbleId) {
  text = (text || '').trim();
  if (!text) return;
  if (curAudio) { curAudio.pause(); curAudio = null; }
  if (text.length <= 32) api('/api/dict/events', { method: 'POST', body: { term: text, action: 'tts', bubble_id: bubbleId || null }, silent: true }).catch(() => {});
  try {
    const url = await media(buildUrl('/api/tts', { text }));
    curAudio = new Audio(url);
    await curAudio.play();
  } catch (e) {
    if (e instanceof ApiError && e.status !== 503 && e.status !== 502) { toast(e.detail, 'error'); return; }
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'zh-CN';
      speechSynthesis.speak(u);
      toast('TTS server lỗi, dùng giọng của trình duyệt', 'info');
    } else toast('Không phát được âm thanh', 'error');
  }
}
const ttsBtn = (text, bubbleId, label = '🔊') =>
  h('button', { class: 'btn small icon', title: 'Phát âm', onclick: (e) => { e.stopPropagation(); speak(text, bubbleId); } }, label);

/* ---------- modal ---------- */
function openModal(title, content) {
  const close = () => { back.remove(); document.removeEventListener('keydown', onKey, true); };
  const onKey = (e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  const body = h('div', { class: 'modal-body' }, content);
  const back = h('div', { class: 'modal-back', onmousedown: (e) => { if (e.target === back) close(); } },
    h('div', { class: 'modal' }, h('div', { class: 'modal-head' }, h('b', {}, title), h('button', { class: 'btn small', onclick: close }, '✕')), body));
  document.body.appendChild(back);
  document.addEventListener('keydown', onKey, true);
  return { close, body };
}

/* ---------- widgets ---------- */
const badge = (text, kind) => h('span', { class: 'badge ' + (kind || text) }, text);
const statusBadge = (s) => badge({ queued: 'Chờ dịch', running: 'Đang dịch', done: 'Xong', failed: 'Lỗi', missing: 'Chưa có' }[s] || s, s);
function field(label, input, hint) {
  return h('label', { class: 'field' }, h('span', {}, label), input, hint ? h('small', {}, hint) : null);
}
function pager(page, size, total, go) {
  const pages = Math.max(1, Math.ceil(total / size));
  return h('div', { class: 'row pager' },
    h('button', { class: 'btn small', disabled: page <= 1, onclick: () => go(page - 1) }, '‹'),
    h('span', {}, `Trang ${page}/${pages} (${total})`),
    h('button', { class: 'btn small', disabled: page >= pages, onclick: () => go(page + 1) }, '›'));
}
async function confirmDo(msg, fn) { if (confirm(msg)) return fn(); }
function tabs(items, active, onSelect) {
  return h('div', { class: 'tabs' }, items.map(([k, label]) =>
    h('button', { class: 'tab' + (k === active ? ' active' : ''), onclick: () => onSelect(k) }, label)));
}

/* ---------- tra từ dùng chung ---------- */
function meaningsList(arr, max = 6) {
  const list = (arr || []).filter(Boolean);
  if (!list.length) return h('span', { class: 'muted' }, '—');
  const ul = h('ul', { class: 'meanings' }, list.slice(0, max).map((m) => h('li', {}, m)));
  if (list.length > max) {
    const more = h('details', {}, h('summary', {}, `+${list.length - max} nghĩa nữa`), h('ul', { class: 'meanings' }, list.slice(max).map((m) => h('li', {}, m))));
    return h('div', {}, ul, more);
  }
  return ul;
}

/** Hiển thị kết quả /api/dict/lookup. opts: bubbleId, onSaved, allowSave */
function renderLookup(d, opts = {}) {
  const root = h('div', { class: 'lookup' });
  const saveBtn = h('button', { class: 'btn primary small' }, d.in_vocab ? 'Thêm ngữ cảnh vào sổ tay' : 'Lưu vào sổ tay');
  const inVocab = h('span', { class: 'muted' }, d.in_vocab ? `Đã trong sổ tay (${d.in_vocab.status})` : '');
  saveBtn.onclick = async () => {
    const res = await safe(api('/api/vocab', { method: 'POST', body: { term: d.term, bubble_id: opts.bubbleId || null, source: opts.source || (opts.bubbleId ? 'highlight' : 'lookup') } }));
    if (!res) return;
    toast(res.created ? 'Đã lưu vào sổ tay' : 'Từ đã có, đã thêm ngữ cảnh', 'ok');
    d.in_vocab = { id: res.id, status: res.status };
    inVocab.textContent = `Đã trong sổ tay (${res.status})`;
    saveBtn.textContent = 'Thêm ngữ cảnh vào sổ tay';
    if (opts.onSaved) opts.onSaved(res);
  };
  root.appendChild(h('div', { class: 'lk-head' },
    h('span', { class: 'zh big' }, d.term), ' ', ttsBtn(d.term, opts.bubbleId)));
  root.appendChild(h('div', { class: 'lk-meta' }, h('b', {}, d.pinyin || ''), d.han_viet ? h('span', { class: 'hv' }, ' · Hán Việt: ' + d.han_viet) : null));
  if (d.summary) root.appendChild(h('p', { class: 'summary' }, d.summary));
  root.appendChild(h('div', { class: 'row' }, saveBtn, inVocab));

  if (d.chars && d.chars.length) {
    root.appendChild(h('h4', {}, 'Từng chữ'));
    root.appendChild(h('div', { class: 'chars' }, d.chars.map((c) => h('button', { class: 'char-chip', title: 'Xem cấu tạo & nét viết', onclick: () => openHanzi(c.ch) },
      h('span', { class: 'zh' }, c.ch), h('small', {}, [c.pinyin, c.han_viet].filter(Boolean).join(' · '))))));
  }
  root.appendChild(h('h4', {}, `Từ điển (${(d.entries || []).length})`));
  if (!(d.entries || []).length) root.appendChild(h('p', { class: 'muted' }, 'Không có mục trong từ điển đầy đủ.'));
  (d.entries || []).forEach((e) => root.appendChild(h('div', { class: 'entry' },
    h('div', {}, h('b', { class: 'zh' }, e.simplified), e.traditional && e.traditional !== e.simplified ? h('span', { class: 'zh muted' }, ` (${e.traditional})`) : null,
      ' ', h('span', {}, e.pinyin || ''), e.han_viet ? h('span', { class: 'hv' }, ' · ' + e.han_viet) : null,
      e.hsk_level ? badge('HSK ' + e.hsk_level, 'hsk') : null, h('small', { class: 'muted' }, ' ' + (e.source || ''))),
    h('div', { class: 'cols' },
      h('div', {}, h('small', { class: 'muted' }, 'Nghĩa Việt'), meaningsList(e.meanings_vi)),
      h('div', {}, h('small', { class: 'muted' }, 'English'), meaningsList(e.meanings_en, 3))))));

  const xx = d.xianxia || {};
  const sec = h('div', { class: 'xianxia' }, h('h4', {}, 'Bộ từ điển tu tiên'));
  let any = false;
  [['phrase', 'Cụm từ (VietPhrase)'], ['name', 'Tên riêng (Names)'], ['char', 'Chữ (PhienAm)']].forEach(([k, label]) => {
    if (xx[k] && xx[k].length) { any = true; sec.appendChild(h('div', {}, h('small', { class: 'muted' }, label), meaningsList(xx[k]))); }
  });
  if (!any) sec.appendChild(h('p', { class: 'muted' }, 'Không có trong bộ tu tiên.'));
  root.appendChild(sec);
  return root;
}

/* ---------- modal chữ Hán + nét viết ---------- */
const SVGNS = 'http://www.w3.org/2000/svg';
const svgEl = (tag, attrs) => { const e = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v); return e; };
let svgUid = 0;

function strokeAnimation(sd) {
  const uid = ++svgUid;
  const svg = svgEl('svg', { viewBox: '0 0 1024 1024', class: 'stroke-svg' });
  svg.appendChild(svgEl('rect', { x: 0, y: 0, width: 1024, height: 1024, fill: 'none', stroke: '#ccc', 'stroke-width': 6 }));
  svg.appendChild(svgEl('line', { x1: 0, y1: 0, x2: 1024, y2: 1024, stroke: '#eee', 'stroke-width': 4 }));
  svg.appendChild(svgEl('line', { x1: 1024, y1: 0, x2: 0, y2: 1024, stroke: '#eee', 'stroke-width': 4 }));
  const g = svgEl('g', { transform: 'scale(1,-1) translate(0,-900)' });
  svg.appendChild(g);
  const strokes = sd.strokes || [], medians = sd.medians || [];
  const defs = svgEl('defs');
  g.appendChild(defs);
  strokes.forEach((d) => g.appendChild(svgEl('path', { d, fill: '#e6e6e6' })));
  const items = strokes.map((d, i) => {
    const clip = svgEl('clipPath', { id: `clip${uid}-${i}` });
    clip.appendChild(svgEl('path', { d }));
    defs.appendChild(clip);
    const grp = svgEl('g', { 'clip-path': `url(#clip${uid}-${i})`, style: 'visibility:hidden' });
    const m = medians[i] || [];
    const pd = m.length ? 'M' + m.map((p) => p.join(' ')).join(' L') : '';
    const line = svgEl('path', { d: pd, fill: 'none', stroke: '#111', 'stroke-width': 180, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
    grp.appendChild(line);
    g.appendChild(grp);
    return { grp, line, d };
  });
  let run = 0;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function play() {
    const my = ++run;
    items.forEach((it) => { it.grp.style.visibility = 'hidden'; });
    for (const it of items) {
      if (my !== run) return;
      let len = 0;
      try { len = it.line.getTotalLength(); } catch (e) { len = 0; }
      it.grp.style.visibility = 'visible';
      if (len > 0) {
        it.line.style.strokeDasharray = len;
        const a = it.line.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 600, fill: 'forwards', easing: 'ease-in-out' });
        await a.finished.catch(() => {});
      } else await sleep(600);
      await sleep(120);
    }
  }
  return { svg, play, stop: () => { run++; } };
}

async function openHanzi(ch) {
  const body = h('div', { class: 'hanzi' }, h('p', { class: 'muted' }, 'Đang tải…'));
  const m = openModal('Chữ Hán: ' + ch, body);
  const d = await safe(api('/api/dict/hanzi/' + encodeURIComponent(ch)));
  if (!d) { m.close(); return; }
  clear(body);
  const info = h('div', { class: 'hanzi-info' },
    h('div', { class: 'zh huge' }, d.ch),
    h('table', { class: 'kv' }, [
      ['Pinyin', d.pinyin], ['Hán Việt', d.han_viet], ['Bộ thủ', d.radical], ['Số nét', d.stroke_count],
      ['Cấu tạo', d.decomposition], ['Nghĩa (EN)', d.definition_en], ['Nguồn gốc', d.etymology && (typeof d.etymology === 'string' ? d.etymology : [d.etymology.type, d.etymology.hint, d.etymology.phonetic && 'âm: ' + d.etymology.phonetic, d.etymology.semantic && 'nghĩa: ' + d.etymology.semantic].filter(Boolean).join(' — '))],
    ].filter(([, v]) => v != null && v !== '').map(([k, v]) => h('tr', {}, h('th', {}, k), h('td', {}, String(v))))),
    d.components && d.components.length ? h('div', {}, h('b', {}, 'Thành phần: '), d.components.map((c) =>
      h('button', { class: 'char-chip small zh', onclick: () => { m.close(); openHanzi(typeof c === 'string' ? c : c.ch || c.char); } }, typeof c === 'string' ? c : c.ch || c.char || JSON.stringify(c)))) : null,
    ttsBtn(d.ch));
  body.appendChild(info);
  if (d.stroke_data && d.stroke_data.strokes && d.stroke_data.strokes.length) {
    const sa = strokeAnimation(d.stroke_data);
    body.appendChild(h('div', { class: 'stroke-box' }, sa.svg,
      h('button', { class: 'btn small', onclick: () => sa.play() }, '↻ Phát lại nét viết')));
    sa.play();
    const mo = new MutationObserver(() => { if (!document.body.contains(sa.svg)) { sa.stop(); mo.disconnect(); } });
    mo.observe(document.body, { childList: true, subtree: true });
  } else body.appendChild(h('p', { class: 'muted' }, 'Chưa có dữ liệu nét viết cho chữ này.'));
}

function lookupBox(term, opts) {
  const box = h('div', {}, h('p', { class: 'muted' }, 'Đang tra…'));
  api('/api/dict/lookup', { query: { term, bubble_id: opts && opts.bubbleId }, silent: true }).then((d) => {
    clear(box).appendChild(renderLookup(d, opts));
  }).catch((e) => { clear(box).appendChild(h('p', { class: 'error' }, e.detail || String(e))); });
  return box;
}
