'use strict';
/* Thư viện: danh sách truyện, chi tiết truyện, chương + upload. */

YH.pages.library = async (ctx) => {
  const { root } = ctx;
  let scope = 'all', q = '';
  const list = h('div', { class: 'grid' });
  const load = async () => {
    const rows = await safe(api('/api/series', { query: { scope, q } }));
    if (!ctx.alive() || !rows) return;
    clear(list);
    if (!rows.length) list.appendChild(h('p', { class: 'muted' }, 'Chưa có truyện nào.'));
    rows.forEach((s) => list.appendChild(h('a', { class: 'card series-card', href: '#/series/' + s.id },
      h('b', {}, s.title_vi), s.title_zh ? h('div', { class: 'zh muted' }, s.title_zh) : null,
      h('div', { class: 'row' }, badge(s.visibility === 'public' ? 'Chung' : 'Riêng tư', s.visibility), badge(s.status === 'completed' ? 'Hoàn thành' : 'Đang ra', s.status),
        h('small', {}, `${s.chapter_count} chương`)),
      s.description ? h('small', { class: 'muted' }, s.description.slice(0, 120)) : null)));
  };
  const scopeTabs = h('div');
  const drawTabs = () => scopeTabs.replaceChildren(tabs([['all', 'Tất cả'], ['public', 'Thư viện chung'], ['mine', 'Của tôi']], scope, (k) => { scope = k; drawTabs(); load(); }));
  drawTabs();
  const search = h('input', { type: 'search', placeholder: 'Tìm theo tên…', oninput: () => { clearTimeout(search._t); search._t = setTimeout(() => { q = search.value.trim(); load(); }, 300); } });

  /* tạo truyện */
  const f = {
    vi: h('input', { required: true, placeholder: 'Tên tiếng Việt *' }), zh: h('input', { placeholder: 'Tên tiếng Trung' }),
    desc: h('textarea', { rows: 2, placeholder: 'Mô tả' }),
    status: h('select', {}, h('option', { value: 'ongoing' }, 'Đang ra'), h('option', { value: 'completed' }, 'Hoàn thành')),
    pub: h('input', { type: 'checkbox' }),
  };
  const createForm = h('form', { class: 'form', onsubmit: async (e) => {
    e.preventDefault();
    const s = await safe(api('/api/series', { method: 'POST', body: { title_vi: f.vi.value, title_zh: f.zh.value || null, description: f.desc.value || null, status: f.status.value, public: f.pub.checked } }));
    if (s) { toast('Đã tạo truyện', 'ok'); location.hash = '#/series/' + s.id; }
  } }, field('Tên (VI)', f.vi), field('Tên (ZH)', f.zh), field('Mô tả', f.desc), field('Trạng thái', f.status),
  YH.user.role === 'admin' ? h('label', { class: 'check' }, f.pub, ' Thư viện chung (admin)') : null,
  h('button', { class: 'btn primary' }, 'Tạo truyện'));

  /* tải nhanh */
  const qFiles = h('input', { type: 'file', multiple: true, accept: 'image/*' });
  const qBtn = h('button', { class: 'btn primary', onclick: async () => {
    if (!qFiles.files.length) return toast('Chọn ảnh trước', 'error');
    const fd = new FormData();
    [...qFiles.files].forEach((x) => fd.append('files', x));
    qBtn.disabled = true;
    const r = await safe(api('/api/uploads/quick', { method: 'POST', body: fd }));
    qBtn.disabled = false;
    if (r) { toast(`Đã tải ${r.pages.length} trang (${r.queued} vào hàng đợi dịch)`, 'ok'); location.hash = '#/chapter/' + r.chapter_id; }
  } }, 'Tải nhanh');

  root.appendChild(h('div', { class: 'page' },
    h('h2', {}, 'Thư viện'),
    h('div', { class: 'row wrap' }, scopeTabs, search),
    list,
    h('div', { class: 'cols' },
      h('details', { class: 'card' }, h('summary', {}, '➕ Tạo truyện mới'), createForm),
      h('div', { class: 'card' }, h('b', {}, 'Tải nhanh'), h('p', { class: 'muted' }, 'Tự tạo chương mới trong truyện riêng “Ảnh tải lên của tôi”.'), qFiles, qBtn))));
  load();
};

YH.pages.series = async (ctx) => {
  const { root } = ctx, id = ctx.args[0];
  const render = async () => {
    const s = await safe(api('/api/series/' + id));
    if (!ctx.alive()) return;
    clear(root);
    if (!s) return root.appendChild(h('p', { class: 'error' }, 'Không tải được truyện.'));
    const parts = [h('a', { href: '#/library' }, '← Thư viện'), h('h2', {}, s.title_vi, s.title_zh ? h('span', { class: 'zh muted' }, '  ' + s.title_zh) : null),
      h('div', { class: 'row' }, badge(s.visibility === 'public' ? 'Chung' : 'Riêng tư', s.visibility), badge(s.status === 'completed' ? 'Hoàn thành' : 'Đang ra', s.status), h('small', {}, s.chapter_count + ' chương')),
      s.description ? h('p', {}, s.description) : null];

    if (s.can_edit) {
      const e = { vi: h('input', { value: s.title_vi }), zh: h('input', { value: s.title_zh || '' }), desc: h('textarea', { rows: 2, value: s.description || '' }),
        st: h('select', {}, h('option', { value: 'ongoing', selected: s.status === 'ongoing' }, 'Đang ra'), h('option', { value: 'completed', selected: s.status === 'completed' }, 'Hoàn thành')) };
      parts.push(h('details', { class: 'card' }, h('summary', {}, '✏️ Sửa / xoá truyện'), h('form', { class: 'form', onsubmit: async (ev) => {
        ev.preventDefault();
        if (await safe(api('/api/series/' + id, { method: 'PATCH', body: { title_vi: e.vi.value, title_zh: e.zh.value || null, description: e.desc.value || null, status: e.st.value } }))) { toast('Đã lưu', 'ok'); render(); }
      } }, field('Tên (VI)', e.vi), field('Tên (ZH)', e.zh), field('Mô tả', e.desc), field('Trạng thái', e.st),
      h('div', { class: 'row' }, h('button', { class: 'btn primary' }, 'Lưu'),
        h('button', { type: 'button', class: 'btn danger', onclick: () => confirmDo('Xoá truyện và toàn bộ chương?', async () => { if (await ok(api('/api/series/' + id, { method: 'DELETE' }))) { toast('Đã xoá', 'ok'); location.hash = '#/library'; } }) }, 'Xoá truyện')))));

      const n = h('input', { type: 'number', step: 'any', min: 0, required: true, placeholder: 'Số chương *' }), t = h('input', { placeholder: 'Tiêu đề' });
      parts.push(h('details', { class: 'card' }, h('summary', {}, '➕ Thêm chương'), h('form', { class: 'form', onsubmit: async (ev) => {
        ev.preventDefault();
        const c = await safe(api(`/api/series/${id}/chapters`, { method: 'POST', body: { number: n.value, title: t.value || null } }));
        if (c) { toast('Đã tạo chương', 'ok'); location.hash = '#/chapter/' + c.id; }
      } }, field('Số chương', n), field('Tiêu đề', t), h('button', { class: 'btn primary' }, 'Tạo chương'))));
    }

    parts.push(h('h3', {}, 'Danh sách chương'));
    const tb = h('table', { class: 'table' }, h('thead', {}, h('tr', {}, ['Số', 'Tiêu đề', 'Trang', 'Tiến độ', ''].map((x) => h('th', {}, x)))));
    const body = h('tbody');
    s.chapters.forEach((c) => {
      const p = c.progress;
      body.appendChild(h('tr', {},
        h('td', {}, fmtNum(c.number)), h('td', {}, h('a', { href: '#/chapter/' + c.id }, c.title || '(không tiêu đề)')), h('td', {}, c.page_count),
        h('td', {}, p ? (p.completed ? '✅ xong' : `trang ${p.last_page_no} (${p.mode === 'learn' ? 'Học' : 'Đọc'})`) : '—'),
        h('td', {}, h('a', { class: 'btn small', href: '#/chapter/' + c.id }, 'Mở'), ' ',
          s.can_edit ? h('button', { class: 'btn small', onclick: () => editChapter(c, render) }, 'Sửa') : null, ' ',
          s.can_edit ? h('button', { class: 'btn small danger', onclick: () => confirmDo('Xoá chương này?', async () => { if (await ok(api('/api/chapters/' + c.id, { method: 'DELETE' }))) render(); }) }, 'Xoá') : null)));
    });
    tb.appendChild(body);
    parts.push(s.chapters.length ? h('div', { class: 'scroll-x' }, tb) : h('p', { class: 'muted' }, 'Chưa có chương.'));
    root.appendChild(h('div', { class: 'page' }, parts));
  };
  render();
};

function editChapter(c, done) {
  const n = h('input', { type: 'number', step: 'any', min: 0, value: fmtNum(c.number) }), t = h('input', { value: c.title || '' });
  const m = openModal('Sửa chương', h('form', { class: 'form', onsubmit: async (e) => {
    e.preventDefault();
    if (await safe(api('/api/chapters/' + c.id, { method: 'PATCH', body: { number: n.value, title: t.value || null } }))) { m.close(); toast('Đã lưu', 'ok'); done(); }
  } }, field('Số chương', n), field('Tiêu đề', t), h('button', { class: 'btn primary' }, 'Lưu')));
}

YH.pages.chapter = async (ctx) => {
  const { root } = ctx, id = ctx.args[0];
  let timer = null;
  ctx.onCleanup(() => clearInterval(timer));
  const holder = h('div', { class: 'page' });
  root.appendChild(holder);

  const render = async (quiet) => {
    const c = await api('/api/chapters/' + id, { silent: !!quiet }).catch(() => null);
    if (!ctx.alive()) return;
    clear(holder);
    if (!c) return holder.appendChild(h('p', { class: 'error' }, 'Không tải được chương.'));
    const busy = c.pages.some((p) => p.status === 'queued' || p.status === 'running');
    clearInterval(timer);
    if (busy) timer = setInterval(() => render(true), 3000);
    const p = c.progress;
    const first = c.pages[0];
    holder.appendChild(h('div', {},
      h('a', { href: '#/series/' + c.series.id }, '← ' + c.series.title_vi),
      h('h2', {}, `Chương ${fmtNum(c.number)}${c.title ? ': ' + c.title : ''}`),
      h('div', { class: 'row wrap' },
        c.prev_chapter_id ? h('a', { class: 'btn small', href: '#/chapter/' + c.prev_chapter_id }, '‹ Chương trước') : null,
        c.next_chapter_id ? h('a', { class: 'btn small', href: '#/chapter/' + c.next_chapter_id }, 'Chương sau ›') : null,
        first ? h('a', { class: 'btn primary', href: '#/read/' + ((p && c.pages.find((x) => x.page_no === p.last_page_no)) || first).id },
          p ? `Đọc tiếp (trang ${p.last_page_no})` : 'Bắt đầu đọc') : null,
        c.can_edit ? h('button', { class: 'btn small', onclick: () => editChapter(c, () => render()) }, 'Sửa chương') : null,
        busy ? h('small', { class: 'muted' }, '⟳ đang cập nhật mỗi 3 giây…') : null)));

    if (c.can_edit) {
      const files = h('input', { type: 'file', multiple: true, accept: 'image/*' });
      const btn = h('button', { class: 'btn primary', onclick: async () => {
        if (!files.files.length) return toast('Chọn ảnh trước', 'error');
        const fd = new FormData();
        [...files.files].forEach((x) => fd.append('files', x));
        btn.disabled = true;
        const r = await safe(api(`/api/chapters/${id}/pages`, { method: 'POST', body: fd }));
        btn.disabled = false;
        if (r) { toast(`Đã thêm ${r.pages.length} trang (${r.queued} dịch mới, ${r.reused} dùng lại)`, 'ok'); render(); }
      } }, 'Tải lên');
      holder.appendChild(h('div', { class: 'card' }, h('b', {}, 'Thêm trang (nhiều ảnh, xếp theo tên file)'), h('div', { class: 'row wrap' }, files, btn)));
    }

    const tb = h('tbody');
    c.pages.forEach((pg) => {
      tb.appendChild(h('tr', {},
        h('td', {}, pg.page_no), h('td', {}, statusBadge(pg.status)),
        h('td', {}, `${pg.width || '?'}×${pg.height || '?'}`),
        h('td', {}, pg.has_original ? '' : h('small', { class: 'error' }, 'ảnh gốc hết hạn'), pg.expires_at ? h('small', { class: 'muted' }, ' hết hạn ' + fmtDate(pg.expires_at)) : null),
        h('td', {}, h('a', { class: 'btn small', href: '#/read/' + pg.id }, 'Đọc'), ' ',
          c.can_edit && (pg.status === 'failed' || pg.status === 'done' || pg.status === 'missing') ? h('button', { class: 'btn small', onclick: async () => {
            if (await safe(api(`/api/pages/${pg.id}/retranslate`, { method: 'POST' }))) { toast('Đã đưa vào hàng đợi dịch lại', 'ok'); render(); }
          } }, pg.status === 'failed' ? '↻ Dịch lại (lỗi)' : '↻ Dịch lại') : null, ' ',
          c.can_edit ? h('button', { class: 'btn small danger', onclick: () => confirmDo('Xoá trang này?', async () => { if (await ok(api('/api/pages/' + pg.id, { method: 'DELETE' }))) render(); }) }, 'Xoá') : null)));
    });
    holder.appendChild(c.pages.length ? h('div', { class: 'scroll-x' }, h('table', { class: 'table' },
      h('thead', {}, h('tr', {}, ['Trang', 'Trạng thái', 'Kích thước', 'Ghi chú', ''].map((x) => h('th', {}, x)))), tb)) : h('p', { class: 'muted' }, 'Chương chưa có trang.'));
  };
  render();
};
