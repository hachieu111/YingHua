import React, { useCallback, useEffect, useState } from 'react';
import { AdminErrorReport, listErrorReports, resolveErrorReport } from '../api/adminSystem';
import { isAbortedError } from '../api/client';
import { ReportStatus } from '../api/notifications';
import { Chip, LoadState, Pager, errorMessage, formatDateTime } from './AdminDataParts';

const PAGE_SIZE = 10;

const STATUS_STYLE: Record<ReportStatus, { label: string; className: string }> = {
  new: { label: 'Mới', className: 'bg-rose-100 text-rose-700' },
  resolved: { label: 'Đã xử lý', className: 'bg-emerald-100 text-emerald-700' },
  rejected: { label: 'Từ chối', className: 'bg-slate-200 text-slate-600' }
};

const TYPE_LABEL: Record<string, string> = { ocr: 'Nhận diện chữ', translation: 'Bản dịch', other: 'Khác' };

interface AdminErrorReportsPanelProps {
  notify: (message: string) => void;
}

/** Báo lỗi nhận diện/bản dịch của người học (F14.02): lọc theo trạng thái, đánh dấu đã xử lý hoặc từ chối kèm ghi chú. */
export const AdminErrorReportsPanel: React.FC<AdminErrorReportsPanelProps> = ({ notify }) => {
  const [status, setStatus] = useState<ReportStatus | null>('new');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: AdminErrorReport[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listErrorReports(status, page, PAGE_SIZE, controller.signal)
      .then(result => {
        setData(result);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được danh sách báo lỗi'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [status, page, tick]);

  const changeStatus = (next: ReportStatus | null) => {
    setStatus(next);
    setPage(1);
    setOpenId(null);
  };

  const resolve = async (report: AdminErrorReport, outcome: 'resolved' | 'rejected') => {
    setBusy(true);
    try {
      await resolveErrorReport(report.id, outcome, note);
      notify(outcome === 'resolved' ? 'Đã đánh dấu báo lỗi là đã xử lý.' : 'Đã từ chối báo lỗi.');
      setOpenId(null);
      setNote('');
      reload();
    } catch (err) {
      notify(errorMessage(err, 'Không cập nhật được báo lỗi'));
    } finally {
      setBusy(false);
    }
  };

  const filters: { value: ReportStatus | null; label: string }[] = [
    { value: 'new', label: 'Mới' },
    { value: 'resolved', label: 'Đã xử lý' },
    { value: 'rejected', label: 'Từ chối' },
    { value: null, label: 'Tất cả' }
  ];

  return (
    <div className="p-4">
      <div className="mb-3 flex flex-wrap gap-1.5">
        {filters.map(filter => (
          <Chip key={filter.label} active={status === filter.value} onClick={() => changeStatus(filter.value)}>{filter.label}</Chip>
        ))}
      </div>
      <LoadState loading={loading && !data} error={error} empty={!!data && data.items.length === 0} emptyText="Không có báo lỗi nào." onRetry={reload} />
      <div className="divide-y divide-slate-100">
        {data?.items.map(report => {
          const style = STATUS_STYLE[report.status];
          const isOpen = openId === report.id;
          return (
            <article key={report.id} className="py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-[10px]">
                    <span className={`rounded-full px-2 py-0.5 font-bold ${style.className}`}>{style.label}</span>
                    <span className="font-semibold text-slate-500">{TYPE_LABEL[report.report_type] ?? report.report_type}</span>
                    <span className="text-slate-400">#{report.id} · {formatDateTime(report.created_at)}</span>
                  </div>
                  <p className="mt-1 text-sm font-semibold text-slate-800">{report.description || 'Không có mô tả'}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {report.series_title ?? 'Truyện đã xóa'}
                    {report.chapter_number !== null && ` · Chương ${report.chapter_number}`}
                    {report.page_no !== null && ` · Trang ${report.page_no}`}
                    {report.reporter && ` · ${report.reporter.display_name}`}
                  </p>
                  {(report.bubble_text_zh || report.bubble_text_vi) && (
                    <p className="mt-1 rounded-lg bg-slate-50 p-2 text-[11px] text-slate-600">
                      {report.bubble_text_zh && <span className="font-['Noto_Serif_SC']">{report.bubble_text_zh}</span>}
                      {report.bubble_text_vi && <span> → {report.bubble_text_vi}</span>}
                    </p>
                  )}
                  {report.resolution_note && <p className="mt-1 text-[11px] text-emerald-700">Ghi chú xử lý: {report.resolution_note}</p>}
                </div>
                {report.status === 'new' && (
                  <button
                    onClick={() => { setOpenId(isOpen ? null : report.id); setNote(''); }}
                    className="rounded-full bg-pink-100 px-3 py-1.5 text-[10px] font-bold text-pink-700"
                  >
                    {isOpen ? 'Đóng' : 'Xử lý'}
                  </button>
                )}
              </div>
              {isOpen && (
                <div className="mt-3 flex flex-col gap-2 rounded-xl bg-blue-50 p-3">
                  <label className="text-[11px] font-semibold text-slate-600" htmlFor={`note-${report.id}`}>Ghi chú xử lý (người báo sẽ thấy)</label>
                  <textarea
                    id={`note-${report.id}`}
                    value={note}
                    maxLength={1000}
                    onChange={event => setNote(event.target.value)}
                    rows={2}
                    className="rounded-lg border border-blue-100 p-2 text-xs outline-none focus:ring-2 focus:ring-pink-200"
                  />
                  <div className="flex justify-end gap-2">
                    <button disabled={busy} onClick={() => void resolve(report, 'rejected')} className="rounded-full bg-white px-4 py-1.5 text-xs font-bold text-slate-600 disabled:opacity-50">Từ chối</button>
                    <button disabled={busy} onClick={() => void resolve(report, 'resolved')} className="rounded-full bg-[#a43073] px-4 py-1.5 text-xs font-bold text-white disabled:opacity-50">Đã xử lý</button>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
      {data && data.total > 0 && <Pager page={page} size={PAGE_SIZE} total={data.total} onPage={setPage} />}
    </div>
  );
};
