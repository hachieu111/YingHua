import React, { useCallback, useEffect, useState } from 'react';
import { ApiSeries, Paged, deleteSeries, listSeries, updateSeries } from '../api/library';
import { isAbortedError } from '../api/client';
import { setSeriesVip } from '../api/rewards';
import { AuthImage } from './AuthImage';
import { Chip, LoadState, Pager, errorMessage } from './AdminDataParts';
import { SeriesManagerModal } from './SeriesManagerModal';

type Scope = 'public' | 'mine';
const PAGE_SIZE = 12;

interface AdminLibraryPanelProps {
  notify: (message: string) => void;
}

/** Kho truyện của quản trị (F03.05, F03.09, F03.11): truyện công khai (kể cả chưa có chương) và truyện riêng của admin. */
export const AdminLibraryPanel: React.FC<AdminLibraryPanelProps> = ({ notify }) => {
  const [scope, setScope] = useState<Scope>('public');
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paged<ApiSeries> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [busyId, setBusyId] = useState<number | null>(null);
  // undefined = đóng; null = thêm truyện mới; số = quản lý truyện đó.
  const [managing, setManaging] = useState<number | null | undefined>(undefined);
  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listSeries({ scope, q: submittedQuery, page, size: PAGE_SIZE }, controller.signal)
      .then(result => {
        setData(result);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err, 'Không tải được kho truyện'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [scope, submittedQuery, page, tick]);

  // Truyện có thể được sửa ở màn khác (Thư viện, trình đọc) nên đọc lại khi quay về tab.
  useEffect(() => {
    const onFocus = () => reload();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [reload]);

  const run = async (id: number, action: () => Promise<unknown>, done: string) => {
    setBusyId(id);
    try {
      await action();
      notify(done);
      reload();
    } catch (err) {
      notify(errorMessage(err, 'Thao tác không thành công, vui lòng thử lại'));
    } finally {
      setBusyId(null);
    }
  };

  const toggleVisibility = (series: ApiSeries) => {
    const target = series.visibility === 'public' ? 'private' : 'public';
    const question =
      target === 'private'
        ? `Chuyển "${series.title_vi}" về riêng tư? Truyện sẽ biến mất khỏi thư viện chung; từ người học đã lưu vẫn giữ ngữ cảnh.`
        : `Đăng "${series.title_vi}" lên thư viện chung?`;
    if (!window.confirm(question)) return;
    void run(series.id, () => updateSeries(series.id, { visibility: target }), target === 'public' ? 'Đã đăng truyện công khai.' : 'Đã chuyển truyện về riêng tư.');
  };

  // Đặt hoặc bỏ cờ VIP của truyện công khai (F17.09); máy chủ cảnh báo nếu truyện VIP chưa có chương đọc thử.
  const toggleVip = async (series: ApiSeries) => {
    setBusyId(series.id);
    try {
      const result = await setSeriesVip(series.id, !series.is_vip);
      notify(result.warning ?? (result.is_vip ? 'Đã đặt truyện là VIP.' : 'Đã bỏ cờ VIP của truyện.'));
      reload();
    } catch (err) {
      notify(errorMessage(err, 'Thao tác không thành công, vui lòng thử lại'));
    } finally {
      setBusyId(null);
    }
  };

  const remove = (series: ApiSeries) => {
    if (!window.confirm(`Xóa truyện "${series.title_vi}" cùng mọi chương và trang? Từ người học đã lưu vẫn được giữ.`)) return;
    void run(series.id, () => deleteSeries(series.id), 'Đã xóa truyện.');
  };

  const switchScope = (next: Scope) => {
    setScope(next);
    setPage(1);
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-[#0f172a] text-slate-800 dark:text-slate-200 shadow-sm dark:shadow-none transition-colors duration-300">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-700 px-4 py-3">
        <h2 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">Kho truyện Manhua</h2>
        <button onClick={() => setManaging(null)} className="rounded-full bg-pink-500 dark:bg-[#a43073] px-3 py-1.5 text-[10px] font-bold text-white">+ Thêm truyện</button>
      </div>
      <div className="flex flex-wrap items-center gap-2 px-4 pt-4">
        <Chip active={scope === 'public'} onClick={() => switchScope('public')}>Truyện công khai</Chip>
        <Chip active={scope === 'mine'} onClick={() => switchScope('mine')}>Truyện riêng của tôi</Chip>
        <form
          onSubmit={event => {
            event.preventDefault();
            setSubmittedQuery(query.trim());
            setPage(1);
          }}
          className="ml-auto flex gap-2"
        >
          <input
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Tìm theo tên truyện..."
            maxLength={100}
            className="w-48 rounded-full border border-slate-200 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-100 dark:placeholder:text-slate-500 px-3 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-pink-200 dark:focus:ring-pink-900/50"
          />
          <button type="submit" className="rounded-full bg-slate-100 dark:bg-slate-800 px-3 py-1.5 text-[11px] font-bold text-slate-600 dark:text-slate-300">Tìm</button>
        </form>
      </div>

      <div className="p-4">
        <LoadState
          loading={loading && !data}
          error={error}
          empty={!!data && data.items.length === 0}
          emptyText={submittedQuery ? 'Không có truyện khớp từ khóa.' : 'Chưa có truyện nào. Bấm "+ Thêm truyện" để tạo.'}
          onRetry={reload}
        />
        {data && data.items.length > 0 && (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {data.items.map(series => (
                <div key={series.id} className="flex gap-3 rounded-xl border border-slate-100 dark:border-slate-700 p-3">
                  <AuthImage src={series.cover_url} alt="Bìa truyện" className="h-20 w-14 shrink-0 rounded-lg bg-slate-100 dark:bg-slate-800 object-cover" />
                  <div className="min-w-0 flex-1">
                    <div className="line-clamp-2 text-xs font-bold">{series.title_vi}</div>
                    {series.title_zh && <div className="truncate text-[10px] text-slate-400 dark:text-slate-500">{series.title_zh}</div>}
                    <div className="mt-1 flex flex-wrap gap-1 text-[9px] font-semibold">
                      <span className={`rounded-full px-2 py-0.5 ${series.visibility === 'public' ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'}`}>
                        {series.visibility === 'public' ? 'Công khai' : 'Riêng tư'}
                      </span>
                      {series.is_vip && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300">VIP</span>}
                      <span className="rounded-full bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 text-blue-700 dark:text-blue-300">{series.chapter_count} chương</span>
                      {series.chapter_count === 0 && series.visibility === 'public' && <span className="rounded-full bg-amber-50 dark:bg-amber-900/30 px-2 py-0.5 text-amber-700 dark:text-amber-400">Chưa có chương</span>}
                      {series.est_hsk_level && <span className="rounded-full bg-pink-50 dark:bg-pink-900/20 px-2 py-0.5 text-[#a43073] dark:text-pink-400">HSK {series.est_hsk_level}</span>}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-bold">
                      <button onClick={() => setManaging(series.id)} className="text-blue-700 dark:text-blue-300">Quản lý nội dung</button>
                      <button disabled={busyId === series.id} onClick={() => toggleVisibility(series)} className="text-slate-600 dark:text-slate-300 disabled:opacity-40">
                        {series.visibility === 'public' ? 'Chuyển riêng tư' : 'Đăng công khai'}
                      </button>
                      {series.visibility === 'public' && (
                        <button disabled={busyId === series.id} onClick={() => void toggleVip(series)} className="text-amber-700 dark:text-amber-400 disabled:opacity-40">
                          {series.is_vip ? 'Bỏ VIP' : 'Đặt VIP'}
                        </button>
                      )}
                      <button disabled={busyId === series.id} onClick={() => remove(series)} className="text-rose-600 dark:text-rose-400 disabled:opacity-40">Xóa</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <Pager page={page} size={PAGE_SIZE} total={data.total} onPage={setPage} />
          </>
        )}
      </div>

      {managing !== undefined && (
        <SeriesManagerModal
          key={managing ?? 'new'}
          isOpen
          seriesId={managing}
          isAdmin
          onClose={() => setManaging(undefined)}
          onChanged={reload}
          showToast={notify}
        />
      )}
    </section>
  );
};
