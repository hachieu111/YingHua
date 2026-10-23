'use strict';
/* Từ điển, Sổ tay, Ôn tập. */

/* ================= Từ điển ================= */
YH.pages.dict = async (ctx) => {
  const { root } = ctx;
  const out = h('div', { class: 'dict-out' });
  const kind = h('select', {}, h('option', { value: '' }, 'Mọi loại'), h('option', { value: 'phrase' }, 'Cụm từ (phrase)'), h('option', { value: 'name' }, 'Tên riêng (name)'), h('option', { value: 'char' }, 'Chữ (char)'));
  const limit = h('input', { type: 'number', min: 1, max: 100, value: 20, style: { width: '70px' } });
  const q = h('input', { placeholder: 'Chữ Hán / pinyin / Hán Việt…', autofocus: true });
  const seg = h('textarea', { rows: 2, placeholder: 'Nhập câu tiếng Trung để tách từ…' });

  const resultTable = (rows, cols) => h('div', { class: 'scroll-x' }, h('table', { class: 'table' }, h('tbody', {}, rows.map(cols))));
  const section = (title, node) => { clear(out).append(h('h3', {}, title), node); };

  const doSearch = async () => {
    const term = q.value.trim(); if (!term) return;
    const rows = await safe(api('/api/dict/search', { query: { q: term, limit: limit.value } }));
    if (!rows) return;
    section(`Từ điển đầy đủ: ${rows.length} kết quả`, rows.length ? resultTable(rows, (e) => h('tr', {},
      h('td', {}, h('a', { href: '#', class: 'zh big', onclick: (ev) => { ev.preventDefault(); doLookup(e.simplified); } }, e.simplified)),
      h('td', {}, e.pinyin), h('td', {}, e.han_viet || ''), h('td', {}, e.summary || ''), h('td', {}, ttsBtn(e.simplified)))) : h('p', { class: 'muted' }, 'Không có kết quả.'));
  };
  const doXianxia = async () => {
    const term = q.value.trim(); if (!term) return;
    const rows = await safe(api('/api/dict/xianxia/search', { query: { q: term, kind: kind.value, limit: limit.value } }));
    if (!rows) return;
    section(`Bộ từ điển tu tiên: ${rows.length} kết quả`, rows.length ? resultTable(rows, (e) => h('tr', {},
      h('td', {}, badge(e.kind, 'hsk')), h('td', {}, h('a', { href: '#', class: 'zh big', onclick: (ev) => { ev.preventDefault(); doLookup(e.key); } }, e.key)),
      h('td', {}, e.pinyin || ''), h('td', {}, (e.meanings || []).join(' ; ')))) : h('p', { class: 'muted' }, 'Không có kết quả.'));
  };
  const doLookup = async (term) => {
    term = (term || q.value).trim(); if (!term) return;
    section('Tra: ' + term, lookupBox(term, {}));
  };
  const doSegment = async () => {
    const text = seg.value.trim(); if (!text) return;
    const toks = await safe(api('/api/dict/segment', { method: 'POST', body: { text } }));
    if (!toks) return;
    section('Tách từ', h('div', { class: 'tokens' }, toks.map((t) => h('button', { class: 'tok', title: t.meaning || '', onclick: () => doLookup(t.w) },
      h('small', {}, t.pinyin || ' '), h('span', { class: 'zh' }, t.w), h('small', { class: 'muted' }, (t.meaning || '').slice(0, 24))))));
  };
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });

  root.appendChild(h('div', { class: 'page' }, h('h2', {}, 'Từ điển'),
    h('div', { class: 'card' }, h('div', { class: 'row wrap' }, q, h('label', {}, 'giới hạn ', limit)),
      h('div', { class: 'row wrap' },
        h('button', { class: 'btn primary', onclick: doSearch }, 'Tìm trong từ điển'),
        h('button', { class: 'btn', onclick: doXianxia }, 'Tìm trong bộ tu tiên'), kind,
        h('button', { class: 'btn', onclick: () => doLookup() }, 'Tra chi tiết (lookup)'),
        h('button', { class: 'btn', onclick: () => { const c = Array.from(q.value.trim())[0]; if (c) openHanzi(c); } }, 'Chữ Hán (chữ đầu)'))),
    h('div', { class: 'card' }, h('b', {}, 'Tách câu'), seg, h('button', { class: 'btn', onclick: doSegment }, 'Tách từ')),
    out));
};

/* ================= Sổ tay ================= */
YH.pages.vocab = async (ctx) => {
  const { root } = ctx;
  if (ctx.args[0]) return vocabDetail(ctx, ctx.args[0]);
  let status = '', q = '', page = 1;
  const size = 20;
  const list = h('div');
  const load = async () => {
    const d = await safe(api('/api/vocab', { query: { status, q, page, size } }));
    if (!ctx.alive() || !d) return;
    clear(list);
    if (!d.items.length) list.appendChild(h('p', { class: 'muted' }, 'Sổ tay trống.'));
    else list.appendChild(h('div', { class: 'scroll-x' }, h('table', { class: 'table' },
      h('thead', {}, h('tr', {}, ['Từ', 'Pinyin', 'Hán Việt', 'Nghĩa', 'Trạng thái', 'Ôn tiếp', ''].map((x) => h('th', {}, x)))),
      h('tbody', {}, d.items.map((v) => h('tr', {},
        h('td', {}, h('a', { class: 'zh big', href: '#/vocab/' + v.id }, v.term)), h('td', {}, v.pinyin), h('td', {}, v.han_viet || ''),
        h('td', {}, v.meaning || ''), h('td', {}, badge(v.status)), h('td', {}, v.next_due ? fmtDate(v.next_due) : '—'),
        h('td', {}, ttsBtn(v.term), ' ', h('a', { class: 'btn small', href: '#/vocab/' + v.id }, 'Chi tiết'))))))));
    list.appendChild(pager(d.page, d.size, d.total, (p) => { page = p; load(); }));
  };
  const st = h('select', { onchange: () => { status = st.value; page = 1; load(); } },
    h('option', { value: '' }, 'Mọi trạng thái'), h('option', { value: 'learning' }, 'Đang học'), h('option', { value: 'known' }, 'Đã thuộc'), h('option', { value: 'ignored' }, 'Bỏ qua'));
  const search = h('input', { type: 'search', placeholder: 'Tìm từ / nghĩa / ghi chú…', oninput: () => { clearTimeout(search._t); search._t = setTimeout(() => { q = search.value.trim(); page = 1; load(); }, 300); } });

  const f = { term: h('input', { required: true, placeholder: 'Từ / cụm chữ Hán *' }), meaning: h('input', { placeholder: 'Nghĩa tuỳ chỉnh' }), note: h('input', { placeholder: 'Ghi chú' }),
    bubble: h('input', { type: 'number', placeholder: 'bubble_id (tuỳ chọn)' }),
    ct: ['recognition', 'recall', 'listening'].map((k) => [k, h('input', { type: 'checkbox', checked: k !== 'listening' })]) };
  const add = h('form', { class: 'form', onsubmit: async (e) => {
    e.preventDefault();
    const r = await safe(api('/api/vocab', { method: 'POST', body: { term: f.term.value.trim(), custom_meaning: f.meaning.value || null, note: f.note.value || null, bubble_id: f.bubble.value ? Number(f.bubble.value) : null, source: 'manual', card_types: f.ct.filter(([, c]) => c.checked).map(([k]) => k) } }));
    if (r) { toast(r.created ? 'Đã thêm' : 'Từ đã có, đã cập nhật', 'ok'); f.term.value = ''; load(); }
  } }, field('Từ', f.term), field('Nghĩa', f.meaning), field('Ghi chú', f.note), field('Bubble ID', f.bubble),
  h('div', { class: 'row' }, f.ct.map(([k, c]) => h('label', { class: 'check' }, c, ' ' + k))), h('button', { class: 'btn primary' }, 'Thêm'));

  root.appendChild(h('div', { class: 'page' }, h('h2', {}, 'Sổ tay từ vựng'),
    h('div', { class: 'row wrap' }, st, search, h('a', { class: 'btn', href: '#/review' }, '▶ Ôn tập')),
    h('details', { class: 'card' }, h('summary', {}, '➕ Thêm từ thủ công'), add), list));
  load();
};

async function vocabDetail(ctx, id) {
  const { root } = ctx;
  const render = async () => {
    const v = await safe(api('/api/vocab/' + id));
    if (!ctx.alive()) return;
    clear(root);
    if (!v) return root.appendChild(h('div', {}, h('a', { href: '#/vocab' }, '← Sổ tay'), h('p', { class: 'error' }, 'Không tải được từ.')));
    const e = { meaning: h('input', { value: v.custom_meaning || '', placeholder: v.meaning || '' }), note: h('textarea', { rows: 2, value: v.note || '' }),
      st: h('select', {}, ['learning', 'known', 'ignored'].map((s) => h('option', { value: s, selected: s === v.status }, { learning: 'Đang học', known: 'Đã thuộc', ignored: 'Bỏ qua' }[s]))) };
    const ctxBubble = h('input', { type: 'number', placeholder: 'bubble_id', style: { width: '120px' } });

    root.appendChild(h('div', { class: 'page' },
      h('a', { href: '#/vocab' }, '← Sổ tay'),
      h('h2', {}, h('span', { class: 'zh' }, v.term), ' ', ttsBtn(v.term), ' ', badge(v.status)),
      h('div', {}, h('b', {}, v.pinyin), v.han_viet ? ' · Hán Việt: ' + v.han_viet : '', h('div', {}, v.meaning || '—'), h('small', { class: 'muted' }, `Nguồn: ${v.source} · tạo ${fmtDate(v.created_at)}`)),
      h('div', { class: 'row' }, Array.from(v.term).map((c) => h('button', { class: 'char-chip small zh', onclick: () => openHanzi(c) }, c))),
      h('details', { class: 'card', open: true }, h('summary', {}, '✏️ Sửa'), h('form', { class: 'form', onsubmit: async (ev) => {
        ev.preventDefault();
        if (await safe(api('/api/vocab/' + id, { method: 'PATCH', body: { custom_meaning: e.meaning.value || null, note: e.note.value || null, status: e.st.value } }))) { toast('Đã lưu', 'ok'); render(); }
      } }, field('Nghĩa tuỳ chỉnh', e.meaning), field('Ghi chú', e.note), field('Trạng thái', e.st),
      h('div', { class: 'row' }, h('button', { class: 'btn primary' }, 'Lưu'),
        h('button', { type: 'button', class: 'btn danger', onclick: () => confirmDo('Xoá từ khỏi sổ tay?', async () => { if (await ok(api('/api/vocab/' + id, { method: 'DELETE' }))) { toast('Đã xoá', 'ok'); location.hash = '#/vocab'; } }) }, 'Xoá từ')))),
      h('h3', {}, 'Ngữ cảnh'),
      v.contexts.length ? v.contexts.map((c) => h('div', { class: 'card ctx' },
        c.snippet_url ? mediaImg(c.snippet_url, { class: 'snippet', alt: 'ảnh bong bóng' }) : null,
        h('div', {}, h('div', { class: 'zh' }, c.sentence_zh), h('div', {}, c.sentence_vi || ''), h('small', { class: 'muted' }, c.source_label || '')),
        h('div', { class: 'row' }, ttsBtn(c.sentence_zh, c.bubble_id), c.page_id ? h('a', { class: 'btn small', href: '#/read/' + c.page_id }, 'Mở trang') : null,
          h('button', { class: 'btn small danger', onclick: () => confirmDo('Xoá ngữ cảnh?', async () => { if (await ok(api('/api/vocab/contexts/' + c.id, { method: 'DELETE' }))) render(); }) }, 'Xoá')))) : h('p', { class: 'muted' }, 'Chưa có ngữ cảnh.'),
      h('div', { class: 'row' }, ctxBubble, h('button', { class: 'btn small', onclick: async () => {
        if (!ctxBubble.value) return toast('Nhập bubble_id', 'error');
        if (await safe(api(`/api/vocab/${id}/contexts`, { method: 'POST', body: { bubble_id: Number(ctxBubble.value) } }))) { toast('Đã thêm ngữ cảnh', 'ok'); render(); }
      } }, '+ Thêm ngữ cảnh từ bubble')),
      h('h3', {}, 'Flashcard'),
      h('div', { class: 'scroll-x' }, h('table', { class: 'table' },
        h('thead', {}, h('tr', {}, ['Loại', 'Trạng thái', 'Đến hạn', 'Khoảng (ngày)', 'Ease', 'Reps/Lapses', 'Tạm ngưng', ''].map((x) => h('th', {}, x)))),
        h('tbody', {}, v.flashcards.map((c) => h('tr', {}, h('td', {}, c.card_type), h('td', {}, badge(c.state)), h('td', {}, fmtDate(c.due_at)), h('td', {}, Number(c.interval_days).toFixed(1)),
          h('td', {}, Number(c.ease_factor).toFixed(2)), h('td', {}, `${c.reps}/${c.lapses}`),
          h('td', {}, h('input', { type: 'checkbox', checked: c.suspended, onchange: async (ev) => { if (!(await safe(api('/api/flashcards/' + c.id, { method: 'PATCH', body: { suspended: ev.target.checked } })))) ev.target.checked = !ev.target.checked; } })),
          h('td', {}, h('button', { class: 'btn small', onclick: () => confirmDo('Học lại thẻ từ đầu?', async () => { if (await safe(api(`/api/flashcards/${c.id}/reset`, { method: 'POST' }))) { toast('Đã reset thẻ', 'ok'); render(); } }) }, 'Reset'))))))),
      h('details', { class: 'card' }, h('summary', {}, 'Tra từ điển'), v.lookup ? renderLookup(v.lookup, {}) : null)));
  };
  render();
}

/* ================= Ôn tập ================= */
YH.pages.review = async (ctx) => {
  const { root } = ctx;
  const stage = h('div', { class: 'review-stage' });
  const counts = h('div', { class: 'row' });
  const hist = h('div');
  let queue = [], idx = 0, flipped = false, t0 = 0, busy = false;

  const load = async () => {
    const d = await safe(api('/api/review/due', { query: { limit: 20 } }));
    if (!ctx.alive() || !d) return;
    queue = d.cards; idx = 0; flipped = false;
    counts.replaceChildren(h('span', {}, 'Đến hạn: ', h('b', {}, d.counts.due)), h('span', {}, 'Thẻ mới còn hôm nay: ', h('b', {}, d.counts.new_today_left)), h('span', {}, 'Đã ôn hôm nay: ', h('b', {}, d.counts.reviewed_today)), h('span', {}, 'Trong hàng: ', h('b', {}, queue.length)));
    show();
  };
  const loadHist = async () => {
    const d = await safe(api('/api/review/history', { query: { days: 30 } }));
    if (!ctx.alive() || !d) return;
    const max = Math.max(1, ...d.map((x) => x.reviews));
    clear(hist).append(h('h3', {}, 'Lịch sử 30 ngày'), d.length ? h('div', { class: 'bars' }, d.map((x) => h('div', { class: 'bar-col', title: `${x.date}: ${x.reviews} lượt, nhớ ${Math.round(x.retention * 100)}%` },
      h('div', { class: 'bar', style: { height: Math.max(4, (x.reviews / max) * 100) + 'px' } }), h('small', {}, x.date.slice(5))))) : h('p', { class: 'muted' }, 'Chưa có lượt ôn.'));
  };

  const cardFront = (c) => {
    const box = h('div', { class: 'cardface' });
    if (c.front === 'term') box.append(h('div', { class: 'zh huge' }, c.vocab.term));
    else if (c.front === 'meaning') {
      box.append(h('div', { class: 'big' }, c.vocab.meaning || '(chưa có nghĩa)'));
      if (c.context && c.context.sentence_vi) box.append(h('p', { class: 'muted' }, c.context.sentence_vi));
    } else box.append(h('button', { class: 'btn big-btn', onclick: () => speak(c.vocab.term) }, '🔊 Nghe'), h('p', { class: 'muted' }, 'Nghe và nhớ lại từ'));
    box.append(h('small', { class: 'muted' }, 'Loại: ' + c.card_type + ' · ' + (c.state)));
    return box;
  };
  const cardBack = (c) => {
    const v = c.vocab, x = c.context;
    return h('div', { class: 'cardface back' },
      h('div', { class: 'zh huge' }, v.term, ' ', ttsBtn(v.term)),
      h('div', {}, h('b', {}, v.pinyin), v.han_viet ? ' · ' + v.han_viet : ''),
      h('div', { class: 'big' }, v.meaning || ''),
      v.note ? h('p', { class: 'muted' }, '📝 ' + v.note) : null,
      x ? h('div', { class: 'ctx' }, x.snippet_url ? mediaImg(x.snippet_url, { class: 'snippet' }) : null,
        h('div', {}, h('div', { class: 'zh' }, x.sentence_zh), h('div', {}, x.sentence_vi || ''), h('small', { class: 'muted' }, x.source_label || ''))) : null);
  };
  const rate = async (r) => {
    if (busy || !flipped) return;
    busy = true;
    const c = queue[idx];
    const res = await safe(api('/api/review/' + c.id, { method: 'POST', body: { rating: r, duration_ms: Math.round(performance.now() - t0) } }));
    busy = false;
    if (!res) return;
    toast(`Lần sau: ${res.next_in}`, 'ok');
    idx++; flipped = false;
    if (idx >= queue.length) { await load(); loadHist(); } else show();
  };
  const flip = () => { if (!flipped && queue[idx]) { flipped = true; show(); } };
  function show() {
    clear(stage);
    const c = queue[idx];
    if (!c) { stage.appendChild(h('div', { class: 'card center' }, h('h3', {}, '🎉 Hết thẻ cần ôn'), h('button', { class: 'btn', onclick: () => { load(); loadHist(); } }, 'Tải lại'))); return; }
    t0 = t0 || performance.now();
    if (!flipped) { t0 = performance.now(); stage.append(h('div', { class: 'card flash', onclick: flip }, cardFront(c)), h('button', { class: 'btn primary', onclick: flip }, 'Lật thẻ (Space)')); if (c.front === 'audio') speak(c.vocab.term); }
    else {
      const names = ['', 'Again', 'Hard', 'Good', 'Easy'];
      stage.append(h('div', { class: 'card flash' }, cardFront(c), h('hr'), cardBack(c)),
        h('div', { class: 'rate' }, [1, 2, 3, 4].map((r) => h('button', { class: 'btn rate' + r, onclick: () => rate(r) }, h('b', {}, `${r}. ${names[r]}`), h('small', {}, c.interval_preview[r])))));
    }
    stage.appendChild(h('small', { class: 'muted' }, `Thẻ ${idx + 1}/${queue.length}`));
  }
  const onKey = (e) => {
    const tag = (e.target.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag) || e.ctrlKey || e.metaKey || e.altKey || document.querySelector('.modal-back')) return;
    if (e.key === ' ') { e.preventDefault(); flip(); }
    else if (['1', '2', '3', '4'].includes(e.key)) rate(Number(e.key));
  };
  document.addEventListener('keydown', onKey);
  ctx.onCleanup(() => document.removeEventListener('keydown', onKey));

  root.appendChild(h('div', { class: 'page' }, h('h2', {}, 'Ôn tập'), counts, stage, hist));
  load(); loadHist();
};
