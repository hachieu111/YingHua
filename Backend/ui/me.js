'use strict';
/* Cá nhân + Admin. */

YH.pages.me = async (ctx) => {
  const { root } = ctx;
  const u = YH.user;
  const dn = h('input', { value: u.display_name });
  const op = h('input', { type: 'password', autocomplete: 'current-password', required: true }), np = h('input', { type: 'password', autocomplete: 'new-password', minlength: 6, maxlength: 72, required: true });

  const account = h('div', { class: 'card' }, h('h3', {}, 'Tài khoản'),
    h('p', {}, h('b', {}, u.email), ' · ', badge(u.role, u.role), h('small', { class: 'muted' }, ` · tạo ${fmtDate(u.created_at)}`)),
    h('form', { class: 'row wrap', onsubmit: async (e) => {
      e.preventDefault();
      const r = await safe(api('/api/auth/me', { method: 'PATCH', body: { display_name: dn.value } }));
      if (r) { YH.user = r; renderNav(); toast('Đã đổi tên hiển thị', 'ok'); }
    } }, dn, h('button', { class: 'btn' }, 'Đổi tên hiển thị')),
    h('details', {}, h('summary', {}, 'Đổi mật khẩu'), h('form', { class: 'form', onsubmit: async (e) => {
      e.preventDefault();
      if (await ok(api('/api/auth/change-password', { method: 'POST', body: { old_password: op.value, new_password: np.value } }))) { toast('Đã đổi mật khẩu, hãy đăng nhập lại', 'ok'); logoutLocal(); }
    } }, field('Mật khẩu cũ', op), field('Mật khẩu mới', np), h('button', { class: 'btn primary' }, 'Đổi mật khẩu'))),
    h('div', { class: 'row' }, h('button', { class: 'btn', onclick: doLogout }, 'Đăng xuất'),
      h('button', { class: 'btn danger', onclick: () => confirmDo('Đăng xuất khỏi mọi thiết bị?', async () => { await ok(api('/api/auth/logout-all', { method: 'POST' })); toast('Đã đăng xuất mọi thiết bị', 'ok'); logoutLocal(); }) }, 'Đăng xuất mọi thiết bị')));

  const settingsBox = h('div', { class: 'card' }, h('h3', {}, 'Cài đặt'));
  const statsBox = h('div', { class: 'card' }, h('h3', {}, 'Thống kê học tập'));
  const progBox = h('div', { class: 'card' }, h('h3', {}, 'Đọc tiếp'));
  root.appendChild(h('div', { class: 'page' }, h('h2', {}, 'Cá nhân'), account, h('div', { class: 'cols' }, settingsBox, progBox), statsBox));

  /* cài đặt */
  Promise.all([safe(api('/api/me/settings')), safe(api('/api/tts/voices'))]).then(([s, voices]) => {
    if (!ctx.alive() || !s) return;
    YH.settings = s;
    const f = {
      hsk: h('input', { type: 'number', min: 0, max: 9, value: s.hsk_level }), nw: h('input', { type: 'number', min: 0, max: 200, value: s.daily_new_cards }),
      cap: h('input', { type: 'number', min: 0, max: 1000, value: s.daily_review_cap }),
      mode: h('select', {}, h('option', { value: 'read', selected: s.default_mode === 'read' }, 'Đọc'), h('option', { value: 'learn', selected: s.default_mode === 'learn' }, 'Học')),
      py: h('input', { type: 'checkbox', checked: s.show_pinyin }),
      voice: h('select', {}, h('option', { value: '' }, '(mặc định)'), (voices || []).map((v) => h('option', { value: v.id, selected: v.id === s.tts_voice }, v.label + ' — ' + v.id))),
    };
    settingsBox.appendChild(h('form', { class: 'form', onsubmit: async (e) => {
      e.preventDefault();
      const r = await safe(api('/api/me/settings', { method: 'PUT', body: { hsk_level: +f.hsk.value, daily_new_cards: +f.nw.value, daily_review_cap: +f.cap.value, default_mode: f.mode.value, show_pinyin: f.py.checked, tts_voice: f.voice.value || null } }));
      if (r) { YH.settings = r; toast('Đã lưu cài đặt', 'ok'); }
    } }, field('Trình độ HSK (0-9)', f.hsk), field('Thẻ mới / ngày', f.nw), field('Giới hạn ôn / ngày', f.cap), field('Chế độ mặc định', f.mode),
    h('label', { class: 'check' }, f.py, ' Hiện pinyin'), field('Giọng đọc', f.voice),
    h('div', { class: 'row' }, h('button', { class: 'btn primary' }, 'Lưu'), h('button', { type: 'button', class: 'btn', onclick: () => speak('你好，欢迎使用英华') }, '🔊 Thử giọng'))));
  });

  /* tiến độ */
  safe(api('/api/me/progress', { query: { limit: 20 } })).then((rows) => {
    if (!ctx.alive() || !rows) return;
    if (!rows.length) progBox.appendChild(h('p', { class: 'muted' }, 'Chưa đọc chương nào.'));
    rows.forEach((p) => progBox.appendChild(h('div', { class: 'prog' },
      h('a', { href: '#/chapter/' + p.chapter_id }, `${p.series_title} · Ch.${p.chapter_number}${p.chapter_title ? ' ' + p.chapter_title : ''}`),
      h('small', { class: 'muted' }, ` trang ${p.last_page_no} (${p.mode === 'learn' ? 'Học' : 'Đọc'})${p.completed ? ' ✅' : ''} · ${fmtDate(p.updated_at)}`))));
  });

  /* thống kê */
  safe(api('/api/me/stats')).then((s) => {
    if (!ctx.alive() || !s) return;
    const stat = (label, val) => h('div', { class: 'stat' }, h('b', {}, val == null ? '—' : val), h('small', {}, label));
    const max = Math.max(1, ...s.forecast_7_days.map((d) => d.due));
    statsBox.append(
      h('div', { class: 'stats' },
        stat('Tổng từ', s.vocab.total), stat('Đang học', s.vocab.learning), stat('Đã thuộc', s.vocab.known), stat('Bỏ qua', s.vocab.ignored),
        stat('Thẻ đến hạn', s.cards.due_now), stat('Thẻ mới', s.cards.new_available), stat('Ôn hôm nay', s.reviews.today), stat('Ôn 30 ngày', s.reviews.last_30_days),
        stat('Tỉ lệ nhớ 30 ngày', s.reviews.retention_30_days == null ? null : Math.round(s.reviews.retention_30_days * 100) + '%'), stat('Chuỗi ngày', s.reviews.streak_days)),
      h('h4', {}, 'Dự báo 7 ngày tới (thẻ đến hạn)'),
      h('div', { class: 'bars' }, s.forecast_7_days.map((d) => h('div', { class: 'bar-col', title: d.date + ': ' + d.due },
        h('small', {}, d.due), h('div', { class: 'bar', style: { height: Math.max(3, (d.due / max) * 100) + 'px' } }), h('small', {}, d.date.slice(5))))),
      h('h4', {}, 'Từ tra nhiều nhất (30 ngày)'),
      s.top_lookups_30_days.length ? h('div', { class: 'row wrap' }, s.top_lookups_30_days.map((t) => h('button', { class: 'char-chip', onclick: () => { const m = openModal('Tra: ' + t.term, lookupBox(t.term, {})); } }, h('span', { class: 'zh' }, t.term), h('small', {}, '×' + t.count)))) : h('p', { class: 'muted' }, 'Chưa có.'));
  });
};

/* ================= Admin ================= */
YH.pages.admin = async (ctx) => {
  const { root } = ctx;
  if (YH.user.role !== 'admin') return root.appendChild(h('p', { class: 'error' }, 'Chỉ dành cho admin.'));
  let tab = 'users';
  const body = h('div');
  const head = h('div');
  const draw = () => {
    head.replaceChildren(tabs([['users', 'Người dùng'], ['trans', 'Bản dịch'], ['stats', 'Hệ thống']], tab, (k) => { tab = k; draw(); }));
    clear(body);
    ({ users: adminUsers, trans: adminTrans, stats: adminStats })[tab](body, ctx);
  };
  root.appendChild(h('div', { class: 'page' }, h('h2', {}, 'Quản trị'), head, body));
  draw();
};

function adminUsers(box, ctx) {
  let q = '', page = 1;
  const size = 20;
  const list = h('div');
  const load = async () => {
    const d = await safe(api('/api/admin/users', { query: { q, page, size } }));
    if (!ctx.alive() || !d) return;
    const patch = async (u, body) => { if (await safe(api('/api/admin/users/' + u.id, { method: 'PATCH', body }))) { toast('Đã cập nhật', 'ok'); load(); } };
    clear(list).append(h('div', { class: 'scroll-x' }, h('table', { class: 'table' },
      h('thead', {}, h('tr', {}, ['ID', 'Email', 'Tên', 'Quyền', 'Hoạt động', 'Đăng nhập cuối', ''].map((x) => h('th', {}, x)))),
      h('tbody', {}, d.items.map((u) => h('tr', {}, h('td', {}, u.id), h('td', {}, u.email), h('td', {}, u.display_name), h('td', {}, badge(u.role, u.role)),
        h('td', {}, u.is_active ? '✔' : '✖ khoá'), h('td', {}, fmtDate(u.last_login_at)),
        h('td', {}, h('button', { class: 'btn small', onclick: () => patch(u, { role: u.role === 'admin' ? 'user' : 'admin' }) }, u.role === 'admin' ? 'Hạ xuống user' : 'Nâng lên admin'), ' ',
          h('button', { class: 'btn small', onclick: () => patch(u, { is_active: !u.is_active }) }, u.is_active ? 'Khoá' : 'Mở khoá'))))))),
    pager(page, size, d.total, (p) => { page = p; load(); }));
  };
  const s = h('input', { type: 'search', placeholder: 'Tìm email / tên…', oninput: () => { clearTimeout(s._t); s._t = setTimeout(() => { q = s.value.trim(); page = 1; load(); }, 300); } });
  box.append(s, list);
  load();
}

function adminTrans(box, ctx) {
  let status = '';
  const list = h('div');
  const load = async () => {
    const d = await safe(api('/api/admin/translations', { query: { status, limit: 100 } }));
    if (!ctx.alive() || !d) return;
    clear(list).append(d.length ? h('div', { class: 'scroll-x' }, h('table', { class: 'table' },
      h('thead', {}, h('tr', {}, ['ID', 'Trạng thái', 'Mode', 'ms', 'Tạo', 'Xong', 'Lỗi', ''].map((x) => h('th', {}, x)))),
      h('tbody', {}, d.map((t) => h('tr', {}, h('td', {}, t.id), h('td', {}, statusBadge(t.status)), h('td', {}, t.mode || ''), h('td', {}, t.processing_ms ?? ''), h('td', {}, fmtDate(t.created_at)), h('td', {}, fmtDate(t.finished_at)),
        h('td', {}, t.error ? h('pre', { class: 'error small' }, t.error) : ''),
        h('td', {}, h('button', { class: 'btn small', onclick: async () => { if (await safe(api(`/api/admin/translations/${t.id}/retry`, { method: 'POST' }))) { toast('Đã xếp lại hàng đợi', 'ok'); load(); } } }, '↻ Retry'))))))) : h('p', { class: 'muted' }, 'Không có bản dịch.'));
  };
  const sel = h('select', { onchange: () => { status = sel.value; load(); } }, h('option', { value: '' }, 'Mọi trạng thái'), ['queued', 'running', 'done', 'failed'].map((s) => h('option', { value: s }, s)));
  box.append(h('div', { class: 'row' }, sel, h('button', { class: 'btn small', onclick: load }, '↻')), list);
  load();
}

function adminStats(box, ctx) {
  safe(api('/api/admin/stats')).then((s) => {
    if (!ctx.alive() || !s) return;
    box.append(h('div', { class: 'stats' }, [['Người dùng', s.users], ['Truyện', s.series], ['Trang', s.pages], ['Từ vựng', s.vocab]].map(([l, v]) => h('div', { class: 'stat' }, h('b', {}, v), h('small', {}, l)))),
      h('h4', {}, 'Bản dịch theo trạng thái'), h('div', { class: 'row' }, Object.entries(s.translations).map(([k, v]) => h('span', {}, statusBadge(k), ' ' + v))),
      h('h4', {}, 'Lưu trữ'), h('table', { class: 'table' }, h('tbody', {}, Object.entries(s.storage).map(([k, v]) => h('tr', {}, h('td', {}, k), h('td', {}, v.files + ' file'), h('td', {}, v.mb + ' MB'))))),
      h('h4', {}, 'Pipeline'), h('pre', {}, JSON.stringify(s.pipeline, null, 2)));
  });
}
