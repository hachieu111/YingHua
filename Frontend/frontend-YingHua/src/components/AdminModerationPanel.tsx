import React, { useCallback, useEffect, useState } from 'react';
import { ModerationUpload, Removal, listModerationUploads, listRemovals, removeContent } from '../api/adminSystem';
import { ApiError, isAbortedError } from '../api/client';
import { AuthImage } from './AuthImage';
import { Chip, LoadState, Pager, errorMessage, formatDateTime } from './AdminDataParts';

const PAGE_SIZE = 12;

const FLAG_LABEL: Record<string, string> = {
  tiny_image: 'Ảnh quá nhỏ',
  oversized_image: 'Ảnh quá lớn',
  duplicate_image: 'Trùng ảnh khác',
  processing_failed: 'Xử lý OCR lỗi'
};

type Tab = 'queue' | 'removed';

interface AdminModerationPanelProps {
  notify: (message: string) => void;
}

const formatSize = (bytes: number): string => (bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/** Kiểm duyệt ảnh tải lên (F13.04): hàng chờ có cờ nghi vấn, gỡ kèm lý do bắt buộc, danh sách đã gỡ. */
export const AdminModerationPanel: React.FC<AdminModerationPanelProps> = ({ notify }) => {
  const [tab, setTab] = useState<Tab>('queue');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [uploads, setUploads] = useState<{ items: ModerationUpload[]; total: number } | null>(null);
  const [removals, setRemovals] = useState<{ items: Removal[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<ModerationUpload | null>(null);
  const [reason, setReason] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const request =
      tab === 'queue'
        ? listModerationUploads(flaggedOnly, page, PAGE_SIZE, controller.signal).then(setUploads)
        : listRemovals(page, PAGE_SIZE, controller.signal).then(setRemovals);
    request
      .then(() => setError(null))
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được dữ liệu kiểm duyệt'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tab, flaggedOnly, page, tick]);

  const openTarget = (upload: ModerationUpload) => {
    setTarget(upload);
    setReason('');
    setConfirming(false);
    setRemoveError(null);
  };

  const confirmRemove = async () => {
    if (!target) return;
    setBusy(true);
    setRemoveError(null);
    try {
      await removeContent({ page_id: target.page_id, file_id: target.file_id }, reason);
      notify('Đã gỡ ảnh vi phạm.');
      setTarget(null);
      reload();
    } catch (err) {
      if (err instanceof ApiError && err.code === 'ALREADY_REMOVED') {
        setRemoveError('Ảnh này đã được gỡ trước đó.');
        reload();
      } else {
        setRemoveError(errorMessage(err, 'Không gỡ được ảnh, vui lòng thử lại'));
      }
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  };

  const changeTab = (next: Tab) => {
    setTab(next);
    setPage(1);
  };

  const list = tab === 'queue' ? uploads : removals;

  return (
    <div className="p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1.5">
          <Chip active={tab === 'queue'} onClick={() => changeTab('queue')}>Hàng chờ kiểm duyệt</Chip>
          <Chip active={tab === 'removed'} onClick={() => changeTab('removed')}>Đã gỡ</Chip>
        </div>
        {tab === 'queue' && (
          <label className="flex items-center gap-2 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={flaggedOnly} onChange={event => { setFlaggedOnly(event.target.checked); setPage(1); }} />
            Chỉ ảnh bị gắn cờ nghi vấn
          </label>
        )}
      </div>

      <LoadState
        loading={loading && !list}
        error={error}
        empty={!!list && list.items.length === 0}
        emptyText={tab === 'queue' ? 'Không có ảnh nào cần kiểm duyệt.' : 'Chưa gỡ nội dung nào.'}
        onRetry={reload}
      />

      {tab === 'queue' && uploads && uploads.items.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {uploads.items.map(upload => (
            <article key={upload.file_id} className="flex gap-3 rounded-xl border border-slate-100 dark:border-slate-700 p-3">
              <AuthImage src={upload.url} alt="Ảnh chờ kiểm duyệt" className="h-24 w-20 shrink-0 rounded-lg object-cover" />
              <div className="flex min-w-0 flex-1 flex-col gap-1 text-[11px] text-slate-600 dark:text-slate-300">
                <div className="flex flex-wrap gap-1">
                  {upload.flags.length === 0 && <span className="rounded-full bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 text-[9px] font-bold text-emerald-700 dark:text-emerald-400">Không nghi vấn</span>}
                  {upload.flags.map(flag => (
                    <span key={flag} className="rounded-full bg-rose-100 dark:bg-rose-900/30 px-2 py-0.5 text-[9px] font-bold text-rose-700 dark:text-rose-400">{FLAG_LABEL[flag] ?? flag}</span>
                  ))}
                  {upload.quick_upload && <span className="rounded-full bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 text-[9px] font-bold text-blue-700 dark:text-blue-300">Tải nhanh</span>}
                </div>
                <span className="truncate font-semibold">{upload.uploader?.display_name ?? 'Người dùng đã xóa'}</span>
                <span className="text-slate-400 dark:text-slate-500">{formatDateTime(upload.uploaded_at)} · {formatSize(upload.size_bytes)}{upload.width && upload.height ? ` · ${upload.width}×${upload.height}` : ''}</span>
                <button onClick={() => openTarget(upload)} className="mt-auto w-fit rounded-full bg-rose-50 dark:bg-rose-900/20 px-3 py-1 text-[10px] font-bold text-rose-700 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-900/40">Gỡ ảnh</button>
              </div>
            </article>
          ))}
        </div>
      )}

      {tab === 'removed' && removals && removals.items.length > 0 && (
        <div className="divide-y divide-slate-100 dark:divide-slate-700">
          {removals.items.map(item => (
            <article key={item.id} className="py-3 text-xs">
              <p className="font-semibold text-slate-800 dark:text-slate-100">{item.reason}</p>
              <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                {formatDateTime(item.removed_at)} · gỡ bởi {item.removed_by?.display_name ?? 'quản trị viên đã xóa'}
                {item.owner && ` · chủ sở hữu ${item.owner.display_name}`}
                {item.page_id !== null && ` · trang #${item.page_id}`}
              </p>
            </article>
          ))}
        </div>
      )}

      {list && list.total > 0 && <Pager page={page} size={PAGE_SIZE} total={list.total} onPage={setPage} />}

      {target && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 dark:bg-black/70 p-4" onClick={busy ? undefined : () => setTarget(null)}>
          <section role="dialog" aria-modal="true" aria-label="Gỡ ảnh vi phạm" className="w-full max-w-md rounded-2xl bg-white dark:bg-[#0f172a] dark:border dark:border-slate-700 p-5 shadow-2xl dark:shadow-none" onClick={event => event.stopPropagation()}>
            <h2 className="text-base font-bold text-slate-800 dark:text-slate-100">Gỡ ảnh vi phạm</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Ảnh sẽ bị ẩn với người dùng và ghi vào nhật ký quản trị. Lý do là bắt buộc.</p>
            <textarea
              value={reason}
              maxLength={2000}
              rows={3}
              onChange={event => setReason(event.target.value)}
              placeholder="Lý do gỡ (vd. nội dung không phù hợp)"
              aria-label="Lý do gỡ"
              className="mt-3 w-full rounded-lg border border-slate-200 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-100 dark:placeholder:text-slate-500 p-2 text-xs outline-none focus:ring-2 focus:ring-pink-200 dark:focus:ring-pink-900/50"
            />
            {removeError && <div role="alert" className="mt-2 rounded-lg bg-rose-50 dark:bg-rose-900/20 p-2 text-xs font-semibold text-rose-700 dark:text-rose-400">{removeError}</div>}
            {confirming && <p className="mt-2 text-xs font-semibold text-rose-700 dark:text-rose-400">Bạn chắc chắn muốn gỡ ảnh này? Thao tác không thể hoàn tác trên giao diện.</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button disabled={busy} onClick={() => setTarget(null)} className="rounded-full px-4 py-2 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700">Hủy</button>
              {!confirming ? (
                <button disabled={!reason.trim()} onClick={() => setConfirming(true)} className="rounded-full bg-[#a43073] px-5 py-2 text-xs font-bold text-white disabled:opacity-40">Tiếp tục</button>
              ) : (
                <button disabled={busy} onClick={() => void confirmRemove()} className="rounded-full bg-rose-600 px-5 py-2 text-xs font-bold text-white disabled:opacity-60">{busy ? 'Đang gỡ...' : 'Xác nhận gỡ'}</button>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
