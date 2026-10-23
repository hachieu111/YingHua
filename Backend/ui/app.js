'use strict';
/* Khởi động: đăng nhập/đăng ký, thanh điều hướng, router theo hash. */

const NAV = [
  ['library', 'Thư viện'], ['dict', 'Từ điển'], ['vocab', 'Sổ tay'], ['review', 'Ôn tập'], ['me', 'Cá nhân'], ['admin', 'Admin'], ['console', 'API Console'],
];
const ALIAS = { series: 'library', chapter: 'library', read: 'library' };

function logoutLocal() {
  clearTokens();
  YH.user = null; YH.settings = null; YH.chapterCache = null; YH.readerMode = null;
  runCleanups(); clearMedia();
  showAuth();
}
async function doLogout() {
  const rt = getRefresh();
  if (rt) await ok(api('/api/auth/logout', { method: 'POST', body: { refresh_token: rt }, silent: true }));
  logoutLocal();
}

function renderNav() {
  const nav = $('#nav');
  if (!nav) return;
  const cur = currentRoute().name;
  const active = ALIAS[cur] || cur;
  clear(nav);
  if (!YH.user) return;
  nav.append(h('b', { class: 'brand' }, '英华 YingHua'),
    h('div', { class: 'navtabs' }, NAV.filter(([k]) => k !== 'admin' || YH.user.role === 'admin').map(([k, label]) =>
      h('a', { class: 'navtab' + (k === active ? ' active' : ''), href: '#/' + k }, label))),
    h('span', { class: 'spacer' }),
    h('a', { class: 'who', href: '#/me', title: YH.user.email }, `${YH.user.display_name} `, badge(YH.user.role, YH.user.role)),
    h('button', { class: 'btn small', onclick: doLogout }, 'Đăng xuất'));
}

function showAuth() {
  clear($('#nav'));
  const root = clear($('#view'));
  let mode = 'login';
  const box = h('div', { class: 'auth card' });
  const draw = () => {
    const email = h('input', { type: 'email', required: true, autocomplete: 'email' });
    const pw = h('input', { type: 'password', required: true, minlength: mode === 'register' ? 6 : 1, maxlength: 72, autocomplete: mode === 'login' ? 'current-password' : 'new-password' });
    const name = h('input', { required: true, maxlength: 100 });
    clear(box).append(
      h('h2', {}, '英华 YingHua'), h('p', { class: 'muted' }, 'Đọc truyện tranh Trung - Việt & học từ vựng'),
      tabs([['login', 'Đăng nhập'], ['register', 'Đăng ký']], mode, (k) => { mode = k; draw(); }),
      h('form', { class: 'form', onsubmit: async (e) => {
        e.preventDefault();
        const body = mode === 'login' ? { email: email.value, password: pw.value } : { email: email.value, password: pw.value, display_name: name.value };
        const d = await safe(api('/api/auth/' + mode, { method: 'POST', body }));
        if (!d) return;
        setTokens(d.access_token, d.refresh_token);
        YH.user = d.user;
        boot();
      } }, field('Email', email), mode === 'register' ? field('Tên hiển thị', name) : null, field('Mật khẩu', pw, mode === 'register' ? '6-72 ký tự' : null), h('button', { class: 'btn primary' }, mode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản')));
  };
  draw();
  root.appendChild(box);
}

/* ---------- router ---------- */
function currentRoute() {
  const parts = (location.hash.replace(/^#\/?/, '') || 'library').split('/');
  return { name: parts[0] || 'library', args: parts.slice(1) };
}
function runCleanups() { YH.cleanups.splice(0).forEach((fn) => { try { fn(); } catch (e) { /* */ } }); }

async function route() {
  if (!YH.user) return;
  runCleanups(); clearMedia();
  const tok = ++YH.token;
  const { name, args } = currentRoute();
  renderNav();
  const view = clear($('#view'));
  window.scrollTo(0, 0);
  const fn = YH.pages[name];
  if (!fn) { view.appendChild(h('p', { class: 'error' }, 'Không có trang: ' + name)); return; }
  const c = { root: view, args, alive: () => YH.token === tok, onCleanup: (f) => YH.cleanups.push(f) };
  try { await fn(c); } catch (e) { console.error(e); view.appendChild(h('p', { class: 'error' }, 'Lỗi giao diện: ' + e.message)); }
}

async function boot() {
  if (!getAccess() && !getRefresh()) return showAuth();
  if (!YH.user) {
    const u = await api('/api/auth/me', { silent: true }).catch(() => null);
    if (!u) return showAuth();
    YH.user = u;
  }
  if (!YH.settings) YH.settings = await api('/api/me/settings', { silent: true }).catch(() => null);
  if (!location.hash) location.hash = '#/library';
  route();
}

window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', boot);
window.addEventListener('unhandledrejection', (e) => { if (!(e.reason instanceof ApiError)) console.error(e.reason); });
