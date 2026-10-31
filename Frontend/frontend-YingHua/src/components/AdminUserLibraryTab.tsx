import React, { useCallback, useEffect, useState } from 'react';
import {
  AdminAnnotation,
  AdminBubbleEdit,
  clearUserAnnotations,
  deleteSeriesAsAdmin,
  deleteUserBubbleEdit,
  getUserAnnotations,
  listUserBookmarks,
  listUserBubbleEdits,
  listUserLibrary,
  listUserQuickUploads,
  listUserReadingProgress,
  updateSeriesAsAdmin
} from '../api/adminUserData';
import { ApiPage, ApiSeries, ContinueItem, LibraryTab, Paged } from '../api/library';
import { BookmarkItem } from '../api/reader';
import { AuthImage } from './AuthImage';
import { ConfirmDialog } from './ConfirmDialog';
import { Chip, errorMessage, formatDateTime, LoadState } from './AdminDataParts';

interface TabProps {
  userId: number;
  notify: (message: string) => void;
}

const FIELD = 'rounded-xl border border-slate-200 px-3 py-2 text-sm font-normal dark:border-slate-700';

/** Tải một danh sách theo `fetcher`; tải lại khi `fetcher` đổi hoặc gọi `reload`. */
function useList<T>(fetcher: () => Promise<T>, fallback: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch(err => setError(errorMessage(err, fallback)))
      .finally(() => setLoading(false));
  }, [fetcher, fallback]);
  useEffect(reload, [reload]);
  return { data, loading, error, reload };
}

const SeriesRow: React.FC<{ series: ApiSeries; userId: number; notify: (m: string) => void; onChanged: () => void }> = ({ series, userId, notify, onChanged }) => {
  const manageable = series.owner_id === userId && series.visibility === 'private';
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(series.title_vi);
  const [author, setAuthor] = useState(series.author ?? '');
  const [description, setDescription] = useState(series.description ?? '');
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    try {
      await action();
      notify(success);
      setEditing(false);
      setConfirming(false);
      onChanged();
    } catch (err) {
      notify(errorMessage(err, 'Thao tác không thành công'));
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    if (!title.trim()) return notify('Tên truyện không được để trống.');
    return run(() => updateSeriesAsAdmin(series.id, { title_vi: title.trim(), author: author.trim() || null, description: description.trim() || null }), 'Đã lưu truyện.');
  };

  return (
    <div className="rounded-xl border border-slate-100 p-3 flex flex-col gap-2 dark:border-slate-700">
      <div className="flex gap-3">
        <AuthImage src={series.cover_url} alt="Bìa truyện" className="w-12 h-16 rounded-lg object-cover shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-bold text-slate-800 truncate dark:text-slate-100">{series.title_vi}</div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">
            {series.visibility === 'private' ? 'Riêng tư' : 'Công khai'} · {series.chapter_count} chương
            {series.progress ? ` · đã đọc ${series.progress.percent}%` : ''}{series.is_favorite ? ' · yêu thích' : ''}
          </div>
        </div>
        {manageable && !editing && (
          <div className="flex gap-2 self-start text-[11px] font-bold">
            <button onClick={() => setEditing(true)} className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">Sửa</button>
            <button onClick={() => setConfirming(true)} className="px-3 py-1 rounded-full bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400">Xóa</button>
          </div>
        )}
      </div>
      {editing && (
        <div className="flex flex-col gap-2">
          <input value={title} maxLength={255} onChange={e => setTitle(e.target.value)} aria-label="Tên truyện" className={FIELD} />
          <input value={author} maxLength={255} onChange={e => setAuthor(e.target.value)} placeholder="Tác giả" aria-label="Tác giả" className={FIELD} />
          <textarea value={description} maxLength={5000} rows={3} onChange={e => setDescription(e.target.value)} placeholder="Mô tả" aria-label="Mô tả" className={FIELD} />
          <div className="flex gap-2">
            <button disabled={busy} onClick={save} className="px-4 py-1.5 rounded-full bg-[#a43073] text-white text-xs font-bold disabled:opacity-50">Lưu</button>
            <button disabled={busy} onClick={() => setEditing(false)} className="px-4 py-1.5 rounded-full bg-slate-100 text-slate-600 text-xs font-bold dark:bg-[#1e293b] dark:text-slate-300">Hủy</button>
          </div>
        </div>
      )}
      {confirming && (
        <ConfirmDialog title="Xóa truyện riêng này?" message={`“${series.title_vi}” cùng toàn bộ chương, trang và bản dịch sẽ bị xóa vĩnh viễn.`}
          confirmLabel="Xóa truyện" busy={busy} onConfirm={() => void run(() => deleteSeriesAsAdmin(series.id), 'Đã xóa truyện.')} onCancel={() => setConfirming(false)} />
      )}
    </div>
  );
};

const LibrarySection: React.FC<TabProps> = ({ userId, notify }) => {
  const [tab, setTab] = useState<LibraryTab>('all');
  const fetcher = useCallback(() => listUserLibrary(userId, tab), [userId, tab]);
  const { data, loading, error, reload } = useList<Paged<ApiSeries>>(fetcher, 'Không tải được Thư viện');
  const tabs: [LibraryTab, string][] = [['all', 'Tất cả'], ['reading', 'Đang đọc'], ['favorites', 'Yêu thích'], ['completed', 'Đã đọc xong']];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2 flex-wrap">{tabs.map(([key, label]) => <Chip key={key} active={tab === key} onClick={() => setTab(key)}>{label}</Chip>)}</div>
      <LoadState loading={loading && !data} error={error} empty={!loading && !error && data?.items.length === 0} emptyText="Thư viện trống" onRetry={reload} />
      {data?.items.map(s => <SeriesRow key={s.id} series={s} userId={userId} notify={notify} onChanged={reload} />)}
    </div>
  );
};

const ProgressSection: React.FC<{ userId: number }> = ({ userId }) => {
  const fetcher = useCallback(() => listUserReadingProgress(userId, 20), [userId]);
  const { data, loading, error, reload } = useList<ContinueItem[]>(fetcher, 'Không tải được tiến độ đọc');
  return (
    <div className="flex flex-col gap-2">
      <LoadState loading={loading && !data} error={error} empty={!loading && !error && data?.length === 0} emptyText="Chưa có truyện đọc dở" onRetry={reload} />
      {data?.map(item => (
        <div key={item.series_id} className="rounded-xl border border-slate-100 p-3 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300">
          <div className="text-sm font-bold text-slate-800 dark:text-slate-100">{item.series_title}</div>
          Chương {item.chapter_number}{item.chapter_title ? ` — ${item.chapter_title}` : ''} · trang {item.page_no}/{item.total_pages} · {item.mode === 'learn' ? 'chế độ học' : 'chế độ đọc'} · {formatDateTime(item.updated_at)}
        </div>
      ))}
    </div>
  );
};

const QuickUploadSection: React.FC<{ userId: number }> = ({ userId }) => {
  const fetcher = useCallback(() => listUserQuickUploads(userId, 1, 24), [userId]);
  const { data, loading, error, reload } = useList<Paged<ApiPage>>(fetcher, 'Không tải được ảnh tải nhanh');
  return (
    <div className="flex flex-col gap-2">
      <LoadState loading={loading && !data} error={error} empty={!loading && !error && data?.items.length === 0} emptyText="Chưa có ảnh tải nhanh" onRetry={reload} />
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
        {data?.items.map(page => (
          <div key={page.id} className="rounded-lg border border-slate-100 overflow-hidden dark:border-slate-700">
            <AuthImage src={page.rendered_url ?? page.original_url} alt={`Ảnh tải nhanh ${page.id}`} className="w-full h-28 object-cover" />
            <div className="px-2 py-1 text-[10px] text-slate-500 dark:text-slate-400">{formatDateTime(page.created_at)}</div>
          </div>
        ))}
      </div>
      {data && data.total > data.items.length && <div className="text-[11px] text-slate-500 dark:text-slate-400">Hiển thị {data.items.length}/{data.total} ảnh mới nhất.</div>}
    </div>
  );
};

/** Ghi chú (tô sáng, nét vẽ) và bản sửa dịch của người dùng trên một trang. */
const PageNotes: React.FC<{ userId: number; pageId: number; notify: (m: string) => void }> = ({ userId, pageId, notify }) => {
  const [annotation, setAnnotation] = useState<AdminAnnotation | null>(null);
  const [edits, setEdits] = useState<AdminBubbleEdit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([getUserAnnotations(userId, pageId), listUserBubbleEdits(userId, pageId)])
      .then(([a, e]) => { setAnnotation(a); setEdits(e.filter(x => x.has_edit)); })
      .catch(err => setError(errorMessage(err, 'Không tải được ghi chú trang')))
      .finally(() => setLoading(false));
  }, [userId, pageId]);

  useEffect(load, [load]);

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true);
    try { await action(); notify(success); setConfirmClear(false); load(); }
    catch (err) { notify(errorMessage(err, 'Thao tác không thành công')); }
    finally { setBusy(false); }
  };

  if (loading || error) return <LoadState loading={loading} error={error} onRetry={load} />;
  const highlights = annotation ? Object.keys(annotation.highlights).length : 0;
  const strokes = annotation?.strokes.length ?? 0;
  return (
    <div className="rounded-lg bg-slate-50 p-3 flex flex-col gap-2 text-xs text-slate-600 dark:bg-[#1e293b] dark:text-slate-300">
      <div className="flex items-center justify-between gap-2">
        <span>Tô sáng: <b>{highlights}</b> · Nét vẽ: <b>{strokes}</b></span>
        {(highlights > 0 || strokes > 0) && <button disabled={busy} onClick={() => setConfirmClear(true)} className="font-bold text-rose-600 disabled:opacity-50 dark:text-rose-400">Xóa ghi chú trang</button>}
      </div>
      {edits.length === 0 ? <div>Không có bản sửa dịch.</div> : edits.map(edit => (
        <div key={edit.bubble_id} className="flex items-start justify-between gap-2 border-t border-slate-200 pt-2 dark:border-slate-700">
          <span>Bóng thoại #{edit.bubble_id}: “{edit.text_vi_effective}”</span>
          <button disabled={busy} onClick={() => void run(() => deleteUserBubbleEdit(userId, edit.bubble_id), 'Đã xóa bản sửa dịch.')} className="shrink-0 font-bold text-rose-600 disabled:opacity-50 dark:text-rose-400">Xóa bản sửa</button>
        </div>
      ))}
      {confirmClear && (
        <ConfirmDialog title="Xóa ghi chú trang?" message="Toàn bộ tô sáng và nét vẽ của người dùng trên trang này sẽ bị xóa."
          confirmLabel="Xóa" busy={busy} onConfirm={() => void run(() => clearUserAnnotations(userId, pageId), 'Đã xóa ghi chú trang.')} onCancel={() => setConfirmClear(false)} />
      )}
    </div>
  );
};

const BookmarkSection: React.FC<TabProps> = ({ userId, notify }) => {
  const fetcher = useCallback(() => listUserBookmarks(userId, 1, 50), [userId]);
  const { data, loading, error, reload } = useList<Paged<BookmarkItem>>(fetcher, 'Không tải được dấu trang');
  const [openPage, setOpenPage] = useState<number | null>(null);
  return (
    <div className="flex flex-col gap-2">
      <LoadState loading={loading && !data} error={error} empty={!loading && !error && data?.items.length === 0} emptyText="Chưa có dấu trang" onRetry={reload} />
      {data?.items.map(item => (
        <div key={item.page_id} className="rounded-xl border border-slate-100 p-3 flex flex-col gap-2 dark:border-slate-700">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-slate-600 min-w-0 dark:text-slate-300">
              <div className="text-sm font-bold text-slate-800 truncate dark:text-slate-100">{item.series_title ?? 'Ảnh tải nhanh'}</div>
              {item.chapter_number !== null ? `Chương ${item.chapter_number} · ` : ''}trang {item.page_no} · {formatDateTime(item.bookmarked_at)}
            </div>
            <button onClick={() => setOpenPage(openPage === item.page_id ? null : item.page_id)} className="shrink-0 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-[11px] font-bold dark:bg-[#1e293b] dark:text-slate-300">
              {openPage === item.page_id ? 'Ẩn ghi chú' : 'Xem ghi chú'}
            </button>
          </div>
          {openPage === item.page_id && <PageNotes userId={userId} pageId={item.page_id} notify={notify} />}
        </div>
      ))}
    </div>
  );
};

type Section = 'library' | 'progress' | 'uploads' | 'bookmarks';

/** Thư viện & đọc truyện của người dùng (F13.07). */
export const AdminUserLibraryTab: React.FC<TabProps> = ({ userId, notify }) => {
  const [section, setSection] = useState<Section>('library');
  const sections: [Section, string][] = [['library', 'Thư viện'], ['progress', 'Tiến độ đọc'], ['uploads', 'Ảnh tải nhanh'], ['bookmarks', 'Dấu trang & ghi chú']];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 flex-wrap">{sections.map(([key, label]) => <Chip key={key} active={section === key} onClick={() => setSection(key)}>{label}</Chip>)}</div>
      {section === 'library' && <LibrarySection userId={userId} notify={notify} />}
      {section === 'progress' && <ProgressSection userId={userId} />}
      {section === 'uploads' && <QuickUploadSection userId={userId} />}
      {section === 'bookmarks' && <BookmarkSection userId={userId} notify={notify} />}
    </div>
  );
};
