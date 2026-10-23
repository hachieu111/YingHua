'use strict';
/* API Console: đọc /openapi.json, chạy được mọi endpoint. */

YH.pages.console = async (ctx) => {
  const { root } = ctx;
  let spec;
  try { spec = await (await fetch('/openapi.json')).json(); } catch (e) { return root.appendChild(h('p', { class: 'error' }, 'Không tải được /openapi.json')); }
  if (!ctx.alive()) return;

  const resolve = (s) => { let n = 0; while (s && s.$ref && n++ < 20) s = spec.components.schemas[s.$ref.split('/').pop()]; return s; };
  const nonNull = (s) => { s = resolve(s); if (s && (s.anyOf || s.oneOf)) return resolve((s.anyOf || s.oneOf).find((x) => x.type !== 'null') || s); return s; };
  const sample = (s, d = 0) => {
    s = nonNull(s);
    if (!s || d > 5) return null;
    if (s.default !== undefined && s.default !== null) return s.default;
    if (s.enum) return s.enum[0];
    switch (s.type) {
      case 'object': { const o = {}; for (const [k, v] of Object.entries(s.properties || {})) o[k] = sample(v, d + 1); return o; }
      case 'array': return [sample(s.items, d + 1)];
      case 'integer': case 'number': return s.minimum != null ? s.minimum : 0;
      case 'boolean': return false;
      case 'string': return s.format === 'email' ? 'user@example.com' : '';
      default: return null;
    }
  };
  const isFile = (s) => { s = nonNull(s); return s && (s.format === 'binary' || s.contentMediaType === 'application/octet-stream'); };

  const ops = [];
  for (const [path, item] of Object.entries(spec.paths)) {
    for (const [method, op] of Object.entries(item)) {
      if (!['get', 'post', 'put', 'patch', 'delete'].includes(method)) continue;
      const params = [...(item.parameters || []), ...(op.parameters || [])].map((p) => ({ ...p, schema: p.schema }));
      ops.push({ method, path, op, params, tag: (op.tags && op.tags[0]) || 'khác' });
    }
  }
  const groups = {};
  ops.forEach((o) => (groups[o.tag] = groups[o.tag] || []).push(o));

  const listEl = h('div', { class: 'console-list' });
  const panel = h('div', { class: 'console-panel' }, h('p', { class: 'muted' }, `Chọn một endpoint bên trái (${ops.length} thao tác).`));
  const filter = h('input', { type: 'search', placeholder: 'Lọc theo path / tên…', oninput: () => drawList() });

  function drawList() {
    const f = filter.value.trim().toLowerCase();
    clear(listEl);
    Object.entries(groups).forEach(([tag, arr]) => {
      const vis = arr.filter((o) => !f || (o.path + ' ' + (o.op.summary || '') + o.method).toLowerCase().includes(f));
      if (!vis.length) return;
      listEl.appendChild(h('details', { open: !!f || undefined }, h('summary', {}, `${tag} (${vis.length})`),
        vis.map((o) => h('div', { class: 'op', onclick: () => select(o) }, h('span', { class: 'm ' + o.method }, o.method.toUpperCase()), h('code', {}, o.path)))));
    });
  }

  function select(o) {
    clear(panel);
    const inputs = [];
    panel.append(h('h3', {}, h('span', { class: 'm ' + o.method }, o.method.toUpperCase()), ' ', h('code', {}, o.path)), o.op.summary ? h('p', {}, o.op.summary) : null, o.op.description ? h('p', { class: 'muted' }, o.op.description) : null);

    if (o.params.length) {
      panel.appendChild(h('h4', {}, 'Tham số'));
      o.params.forEach((p) => {
        const sc = nonNull(p.schema) || {};
        let input;
        if (sc.enum) input = h('select', {}, h('option', { value: '' }, '(bỏ trống)'), sc.enum.map((v) => h('option', { value: v }, v)));
        else if (sc.type === 'boolean') input = h('select', {}, h('option', { value: '' }, '(bỏ trống)'), h('option', { value: 'true' }, 'true'), h('option', { value: 'false' }, 'false'));
        else input = h('input', { placeholder: sc.default != null ? 'mặc định: ' + sc.default : (sc.type || 'string'), value: p.in === 'path' ? '' : '' });
        inputs.push({ p, input });
        panel.appendChild(field(`${p.name}${p.required ? ' *' : ''} (${p.in})`, input, p.description));
      });
    }

    let bodyKind = null, bodyArea = null, mpInputs = [];
    const rb = o.op.requestBody;
    if (rb && rb.content) {
      if (rb.content['application/json']) {
        bodyKind = 'json';
        bodyArea = h('textarea', { rows: 8, class: 'code', value: JSON.stringify(sample(rb.content['application/json'].schema), null, 2) });
        panel.append(h('h4', {}, 'Body (JSON)'), bodyArea);
      } else if (rb.content['multipart/form-data']) {
        bodyKind = 'multipart';
        const sc = resolve(rb.content['multipart/form-data'].schema);
        panel.appendChild(h('h4', {}, 'Body (multipart)'));
        Object.entries(sc.properties || {}).forEach(([name, ps]) => {
          const nn = nonNull(ps);
          const arrFile = nn && nn.type === 'array' && isFile(nn.items);
          const file = arrFile || isFile(ps);
          const input = file ? h('input', { type: 'file', multiple: !!arrFile }) : h('input', { placeholder: name });
          mpInputs.push({ name, input, file });
          panel.appendChild(field(name + (file ? ' (file)' : ''), input));
        });
      }
    }

    const out = h('div', { class: 'console-out' });
    const send = h('button', { class: 'btn primary', onclick: async () => {
      let path = o.path;
      const query = {};
      for (const { p, input } of inputs) {
        const v = input.value;
        if (p.in === 'path') {
          if (v === '') return toast(`Thiếu tham số path: ${p.name}`, 'error');
          path = path.replace('{' + p.name + '}', encodeURIComponent(v));
        } else if (p.in === 'query' && v !== '') query[p.name] = v;
      }
      const opts = { method: o.method.toUpperCase(), query, raw: true };
      if (bodyKind === 'json') {
        try { opts.body = bodyArea.value.trim() ? JSON.parse(bodyArea.value) : undefined; } catch (e) { return toast('JSON không hợp lệ: ' + e.message, 'error'); }
      } else if (bodyKind === 'multipart') {
        const fd = new FormData();
        mpInputs.forEach(({ name, input, file }) => {
          if (file) [...input.files].forEach((f) => fd.append(name, f));
          else if (input.value !== '') fd.append(name, input.value);
        });
        opts.body = fd;
      }
      clear(out).appendChild(h('p', { class: 'muted' }, 'Đang gửi…'));
      const t0 = performance.now();
      let r;
      try { r = await api(path, opts); } catch (e) { return clear(out).appendChild(h('p', { class: 'error' }, 'Lỗi mạng/phiên: ' + (e.detail || e.message))); }
      const ms = Math.round(performance.now() - t0);
      const ct = r.headers.get('content-type') || '';
      const head = h('div', { class: 'row' }, h('span', { class: 'badge ' + (r.ok ? 'done' : 'failed') }, `${r.status} ${r.statusText}`), h('small', {}, `${ms} ms · ${ct || 'no body'}`),
        h('code', {}, buildUrl(path, query)));
      clear(out).appendChild(head);
      if (ct.startsWith('image/')) { const u = URL.createObjectURL(await r.blob()); out.appendChild(h('img', { src: u, class: 'resp-img' })); }
      else if (ct.startsWith('audio/')) { const u = URL.createObjectURL(await r.blob()); out.appendChild(h('audio', { src: u, controls: true })); }
      else if (ct.includes('json')) { out.appendChild(h('pre', { class: 'resp' }, JSON.stringify(await r.json(), null, 2))); }
      else { const txt = await r.text(); out.appendChild(h('pre', { class: 'resp' }, txt || '(không có nội dung)')); }
    } }, 'Gửi request');
    panel.append(send, out);
  }

  drawList();
  root.appendChild(h('div', { class: 'page wide' }, h('h2', {}, 'API Console'), h('div', { class: 'console' }, h('div', { class: 'console-side' }, filter, listEl), panel)));
};
