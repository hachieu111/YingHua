import React, { useCallback, useEffect, useState } from 'react';
import { AuditFilter, AuditLog, listAuditLogs } from '../api/adminSystem';
import { isAbortedError } from '../api/client';
import { LoadState, Pager, errorMessage, formatDateTime } from './AdminDataParts';

const PAGE_SIZE = 20;

const EMPTY_FILTER: AuditFilter = { adminId: null, action: '', targetType: '', since: '', until: '' };

const KNOWN_ACTIONS = ['user.locked', 'user.unlocked', 'user.role_changed', 'settings.updated', 'content.removed'];

const ACTION_LABEL: Record<string, string> = {
  'user.locked': 'Khóa tài khoản',
  'user.unlocked': 'Mở khóa tài khoản',
  'user.role_changed': 'Đổi vai trò',
  'settings.updated': 'Đổi cài đặt hệ thống',
  'content.removed': 'Gỡ nội dung vi phạm'
};

const inputClass = 'rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-pink-200';

/** Nhật ký thao tác của quản trị viên (F13.06): lọc theo người làm, loại thao tác, đối tượng, khoảng ngày. */
export const AdminAuditPanel: React.FC = () => {
  const [form, setForm] = useState<AuditFilter>(EMPTY_FILTER);
  const [applied, setApplied] = useState<AuditFilter>(EMPTY_FILTER);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: AuditLog[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listAuditLogs(applied, page, PAGE_SIZE, controller.signal)
      .then(result => {
        setData(result);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được nhật ký quản trị'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [applied, page, tick]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setApplied(form);
    setPage(1);
  };

  const clear = () => {
    setForm(EMPTY_FILTER);
    setApplied(EMPTY_FILTER);
    setPage(1);
  };

  return (
    <div className="p-4">
      <form onSubmit={submit} className="mb-3 flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-[10px] font-semibold text-slate-500">
          Mã người thực hiện
          <input
            type="number"
            min={1}
            value={form.adminId ?? ''}
            onChange={event => setForm({ ...form, adminId: event.target.value ? Number(event.target.value) : null })}
            className={`${inputClass} w-28`}
          />
        </label>
        <label className="flex flex-col gap-1 text-[10px] font-semibold text-slate-500">
          Thao tác
          <input list="audit-actions" maxLength={48} value={form.action} onChange={event => setForm({ ...form, action: event.target.value })} className={`${inputClass} w-44`} />
          <datalist id="audit-actions">{KNOWN_ACTIONS.map(action => <option key={action} value={action} />)}</datalist>
        </label>
        <label className="flex flex-col gap-1 text-[10px] font-semibold text-slate-500">
          Đối tượng
          <input maxLength={32} value={form.targetType} onChange={event => setForm({ ...form, targetType: event.target.value })} className={`${inputClass} w-32`} />
        </label>
        <label className="flex flex-col gap-1 text-[10px] font-semibold text-slate-500">
          Từ ngày
          <input type="date" value={form.since} onChange={event => setForm({ ...form, since: event.target.value })} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-[10px] font-semibold text-slate-500">
          Đến ngày
          <input type="date" value={form.until} onChange={event => setForm({ ...form, until: event.target.value })} className={inputClass} />
        </label>
        <button type="submit" className="rounded-full bg-[#a43073] px-4 py-2 text-xs font-bold text-white hover:bg-[#85145a]">Lọc</button>
        <button type="button" onClick={clear} className="rounded-full bg-slate-100 px-4 py-2 text-xs font-bold text-slate-600">Xóa lọc</button>
      </form>

      <LoadState loading={loading && !data} error={error} empty={!!data && data.items.length === 0} emptyText="Không có bản ghi nào khớp bộ lọc." onRetry={reload} />
      <div className="divide-y divide-slate-100">
        {data?.items.map(log => (
          <article key={log.id} className="py-3 text-xs">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-bold text-slate-800">{ACTION_LABEL[log.action] ?? log.action}</span>
              <span className="text-[10px] text-slate-400">{log.action}</span>
              <span className="text-[11px] text-slate-500">{log.admin ? `${log.admin.display_name} (#${log.admin.id})` : 'Quản trị viên đã xóa'}</span>
              <span className="text-[11px] text-slate-500">{log.target_type}{log.target_id !== null ? ` #${log.target_id}` : ''}</span>
              <span className="ml-auto text-[11px] text-slate-400">{formatDateTime(log.created_at)}</span>
            </div>
            {Object.keys(log.details).length > 0 && (
              <p className="mt-1 break-words rounded-lg bg-slate-50 p-2 font-mono text-[10px] text-slate-600">
                {Object.entries(log.details).map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`).join(' · ')}
              </p>
            )}
          </article>
        ))}
      </div>
      {data && data.total > 0 && <Pager page={page} size={PAGE_SIZE} total={data.total} onPage={setPage} />}
    </div>
  );
};
