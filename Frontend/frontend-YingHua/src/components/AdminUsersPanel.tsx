import React, { useCallback, useEffect, useState } from 'react';
import { AdminUser, changeUserRole, listUsers, lockUser, unlockUser } from '../api/adminUsers';
import { ApiError } from '../api/client';
import { AdminUserDataDrawer } from './AdminUserDataDrawer';

interface AdminUsersPanelProps {
  currentUserEmail: string;
  searchQuery: string;
  notify: (message: string) => void;
}

type StatusFilter = 'Tất cả' | 'Đang hoạt động' | 'Bị khóa';

const PAGE_SIZE = 10;

/** Quản lý người dùng thật (F13.01–F13.03): danh sách + tìm theo email, đổi vai trò, khóa/mở khóa. */
export const AdminUsersPanel: React.FC<AdminUsersPanelProps> = ({ currentUserEmail, searchQuery, notify }) => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<StatusFilter>('Tất cả');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<AdminUser | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listUsers({ q: searchQuery, page, size: PAGE_SIZE });
      setUsers(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Không tải được danh sách người dùng');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, page]);

  useEffect(() => {
    // Chờ người dùng ngừng gõ rồi mới gọi API.
    const timer = window.setTimeout(load, 300);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => setPage(1), [searchQuery]);

  const replaceUser = (updated: AdminUser) =>
    setUsers(current => current.map(user => (user.id === updated.id ? updated : user)));

  const act = async (user: AdminUser, action: () => Promise<AdminUser>, successMessage: string) => {
    setBusyId(user.id);
    try {
      replaceUser(await action());
      notify(successMessage);
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Thao tác không thành công');
    } finally {
      setBusyId(null);
    }
  };

  const toggleLock = (user: AdminUser) => {
    if (user.status === 'locked') {
      return act(user, () => unlockUser(user.id), `Đã mở khóa ${user.email}.`);
    }
    const reason = window.prompt(`Lý do khóa tài khoản ${user.email} (có thể bỏ trống):`);
    if (reason === null) return Promise.resolve(); // Hủy xác nhận: không thay đổi.
    return act(user, () => lockUser(user.id, reason), `Đã khóa ${user.email}.`);
  };

  const toggleRole = (user: AdminUser) => {
    const next = user.role === 'admin' ? 'user' : 'admin';
    const label = next === 'admin' ? 'Quản trị viên' : 'Học viên';
    if (!window.confirm(`Đổi vai trò của ${user.email} thành ${label}?`)) return Promise.resolve();
    return act(user, () => changeUserRole(user.id, next), `Đã đổi vai trò ${user.email} thành ${label}.`);
  };

  const visible = users.filter(user =>
    filter === 'Tất cả' || (filter === 'Bị khóa' ? user.status === 'locked' : user.status === 'active')
  );
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="rounded-2xl border border-slate-100 bg-white overflow-hidden">
      <div className="flex gap-2 p-4 border-b border-slate-100">
        {(['Tất cả', 'Đang hoạt động', 'Bị khóa'] as const).map(value => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className={`px-3 py-1.5 rounded-full text-[11px] font-semibold ${filter === value ? 'bg-pink-500 text-white' : 'bg-slate-100 text-slate-600'}`}
          >
            {value}
          </button>
        ))}
        <span className="ml-auto self-center text-[11px] text-slate-500">{total} người dùng</span>
      </div>

      {error && <div role="alert" className="p-4 text-xs font-semibold text-rose-600">{error}</div>}

      <div className="divide-y divide-slate-100">
        {visible.map(user => {
          const isSelf = user.email === currentUserEmail;
          const locked = user.status === 'locked';
          return (
            <div key={user.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0">
                <div className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <span className="truncate">{user.display_name}</span>
                  {user.role === 'admin' && <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[9px] font-bold text-blue-700">Quản trị viên</span>}
                  {locked && <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[9px] font-bold text-rose-700">Đã khóa</span>}
                </div>
                <div className="text-xs text-slate-500 truncate">
                  {user.email} · Tham gia {new Date(user.created_at).toLocaleDateString('vi-VN')}
                  {locked && user.locked_reason ? ` · Lý do: ${user.locked_reason}` : ''}
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => setViewing(user)}
                  className="px-3 py-1.5 rounded-full bg-pink-50 text-[#a43073] text-xs font-bold"
                >
                  Xem dữ liệu
                </button>
                <button
                  disabled={isSelf || busyId === user.id}
                  onClick={() => toggleRole(user)}
                  title={isSelf ? 'Không thể tự đổi vai trò của chính mình' : undefined}
                  className="px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 text-xs font-bold disabled:opacity-40"
                >
                  {user.role === 'admin' ? 'Hạ xuống Học viên' : 'Nâng lên Quản trị'}
                </button>
                <button
                  disabled={isSelf || busyId === user.id}
                  onClick={() => toggleLock(user)}
                  title={isSelf ? 'Không thể tự khóa chính mình' : undefined}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold disabled:opacity-40 ${locked ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}
                >
                  {locked ? 'Mở khóa' : 'Khóa'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {!loading && visible.length === 0 && !error && (
        <div className="p-8 text-center text-sm text-slate-500">Không tìm thấy người dùng</div>
      )}
      {loading && <div className="p-4 text-center text-xs text-slate-400">Đang tải...</div>}

      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-[11px] text-slate-500">
        <span>Trang {page}/{totalPages}</span>
        <div className="flex gap-1">
          <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-3 py-1 rounded-full bg-slate-100 disabled:opacity-40">Trước</button>
          <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-3 py-1 rounded-full bg-slate-100 disabled:opacity-40">Sau</button>
        </div>
      </div>
      {viewing && <AdminUserDataDrawer user={viewing} onClose={() => setViewing(null)} notify={notify} />}
    </div>
  );
};
