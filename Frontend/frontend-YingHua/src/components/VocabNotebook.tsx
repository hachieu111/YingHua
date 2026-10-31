import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { hskLabel } from '../api/dictionary';
import { ApiVocabItem, VocabExportFormat, VocabStatus, deleteVocab, exportVocab, isExportEmpty, listVocab, updateVocab } from '../api/vocab';
import { ReaderTarget } from '../types';
import { speakChinese } from '../utils/speech';
import { ConfirmDialog } from './ConfirmDialog';
import { DismissedSuggestions } from './DismissedSuggestions';
import { VocabDetailModal } from './VocabDetailModal';

interface VocabNotebookProps {
  /** Tăng lên khi nơi khác (phòng ôn, bộ thẻ) làm đổi dữ liệu Sổ tay. */
  refreshKey: number;
  /** Tăng lên khi người học bấm "Xáo trộn": trộn thứ tự hiển thị trong phiên, không đổi dữ liệu. */
  shuffleTick: number;
  onChanged: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  onNavigateToReader: () => void;
  showToast: (message: string) => void;
}

type StatusFilter = 'all' | VocabStatus | 'due';
type HskFilter = 'all' | 'none' | number;

const PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 350;
const HSK_LEVELS = [1, 2, 3, 4, 5, 6, 7];

const STATUS_LABEL: Record<VocabStatus, string> = { learning: 'Đang học', known: 'Đã thuộc', ignored: 'Tạm bỏ qua' };
const STATUS_STYLE: Record<VocabStatus, string> = {
  learning: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
  known: 'bg-[#ffd8e7] dark:bg-pink-900/30 text-[#a43073] dark:text-pink-300',
  ignored: 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
};

const shuffled = <T,>(items: T[]): T[] => {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

export const VocabNotebook: React.FC<VocabNotebookProps> = ({ refreshKey, shuffleTick, onChanged, onOpenReader, onNavigateToReader, showToast }) => {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [hskFilter, setHskFilter] = useState<HskFilter>('all');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<ApiVocabItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ApiVocabItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    // "Cần ôn lại" lọc ở máy chủ: chỉ các từ có thẻ đến hạn (F07.04).
    const dueOnly = statusFilter === 'due';
    listVocab(
      {
        status: dueOnly || statusFilter === 'all' ? undefined : statusFilter,
        due: dueOnly ? true : undefined,
        hsk: hskFilter === 'all' ? undefined : hskFilter,
        q: debouncedQuery || undefined,
        page,
        size: PAGE_SIZE
      },
      controller.signal
    )
      .then(result => {
        setItems(result.items);
        setTotal(result.total);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [statusFilter, hskFilter, debouncedQuery, page, reloadTick, refreshKey]);

  const reload = useCallback(() => setReloadTick(value => value + 1), []);

  const visibleItems = useMemo(() => (shuffleTick > 0 ? shuffled(items) : items), [items, shuffleTick]);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const patchItem = (id: number, patch: Partial<ApiVocabItem>) =>
    setItems(current => current.map(item => (item.id === id ? { ...item, ...patch } : item)));

  const handleToggleStar = async (item: ApiVocabItem) => {
    setBusyId(item.id);
    try {
      const updated = await updateVocab(item.id, { is_starred: !item.is_starred });
      patchItem(item.id, { is_starred: updated.is_starred });
      onChanged();
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleStatusChange = async (item: ApiVocabItem, status: VocabStatus) => {
    setBusyId(item.id);
    try {
      const updated = await updateVocab(item.id, { status });
      patchItem(item.id, { status: updated.status, is_due: updated.is_due });
      onChanged();
      showToast(`Đã chuyển “${item.term}” sang “${STATUS_LABEL[status]}”`);
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteVocab(deleteTarget.id);
      showToast(`Đã xóa “${deleteTarget.term}” khỏi Sổ tay`);
      setDeleteTarget(null);
      if (items.length === 1 && page > 1) setPage(page - 1);
      reload();
      onChanged();
    } catch (err) {
      showToast(errorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  // Xuất theo đúng bộ lọc đang áp dụng (F07.08); tệp tạo bằng blob: URL rồi thu hồi ngay sau khi tải.
  const handleExport = async (format: VocabExportFormat) => {
    setExportOpen(false);
    setExporting(true);
    try {
      const dueOnly = statusFilter === 'due';
      const file = await exportVocab(format, {
        status: dueOnly || statusFilter === 'all' ? undefined : statusFilter,
        due: dueOnly ? true : undefined,
        hsk: hskFilter === 'all' ? undefined : hskFilter,
        q: debouncedQuery || undefined
      });
      const objectUrl = URL.createObjectURL(file.blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = file.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
      showToast(`Đã xuất Sổ tay (${format === 'csv' ? 'CSV' : 'Anki'}).`);
    } catch (err) {
      showToast(isExportEmpty(err) ? 'Không có từ nào để xuất theo bộ lọc hiện tại.' : errorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const filtersActive = statusFilter !== 'all' || hskFilter !== 'all' || debouncedQuery !== '';

  return (
    <>
      {/* HSK LEVEL CHIP SELECTOR */}
      <div className="p-6 rounded-3xl bg-[#eff4ff] dark:bg-[#0f172a] flex flex-col md:flex-row items-center justify-between gap-4 border border-blue-100 dark:border-slate-800 shadow-xs dark:shadow-none transition-colors duration-300">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-amber-200 dark:bg-amber-900/40 text-amber-900 dark:text-amber-300 flex items-center justify-center font-bold text-sm shrink-0">HSK</div>
          <div>
            <div className="text-sm font-bold text-slate-800 dark:text-white">Lọc Sổ tay theo Cấp Độ Chuẩn HSK 3.0</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">Xem nhanh các từ đã lưu từ Manhua phù hợp với trình độ thi cử của bạn</div>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {HSK_LEVELS.map(level => (
            <button
              key={level}
              onClick={() => {
                setHskFilter(hskFilter === level ? 'all' : level);
                setPage(1);
              }}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                hskFilter === level ? 'bg-[#a43073] text-white shadow-xs' : 'bg-white dark:bg-[#1e293b] text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200/60 dark:border-slate-700'
              }`}
            >
              {hskLabel(level)} {level === 4 && '🔥'}
            </button>
          ))}
          <button
            onClick={() => {
              setHskFilter(hskFilter === 'none' ? 'all' : 'none');
              setPage(1);
            }}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
              hskFilter === 'none' ? 'bg-[#a43073] text-white shadow-xs' : 'bg-white dark:bg-[#1e293b] text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200/60 dark:border-slate-700'
            }`}
          >
            Ngoài HSK
          </button>
          <button
            onClick={() => {
              setHskFilter('all');
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-full text-xs font-bold ${hskFilter === 'all' ? 'bg-[#0060ac] text-white' : 'bg-white dark:bg-[#1e293b] text-slate-600 dark:text-slate-300'}`}
          >
            Tất cả
          </button>
        </div>
      </div>

      {/* DETAILED VOCABULARY DATA TABLE */}
      <div className="bg-white dark:bg-[#0f172a] rounded-3xl p-6 sm:p-8 shadow-soft dark:shadow-none border border-pink-100 dark:border-slate-800 transition-colors duration-300 flex flex-col gap-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2">
          <div>
            <h3 className="text-xl font-bold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">Danh Sách Chi Tiết Từ Vựng Đã Lưu</h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {filtersActive ? `Tìm thấy ${total} từ phù hợp bộ lọc` : `Tổng cộng ${total} từ đã lưu trong Sổ tay`}
            </span>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <span className="material-symbols-outlined absolute left-3 top-2.5 text-slate-400 dark:text-slate-500 text-[18px]">search</span>
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Tìm Hán tự, Pinyin, nghĩa..."
                maxLength={64}
                className="w-full pl-9 pr-3 py-1.5 rounded-full bg-slate-50 dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-[#f472b6] transition-all"
              />
            </div>

            <select
              value={statusFilter}
              onChange={e => {
                setStatusFilter(e.target.value as StatusFilter);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-full bg-slate-50 dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 outline-none cursor-pointer"
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="known">Đã thuộc</option>
              <option value="learning">Đang học</option>
              <option value="due">Cần ôn lại</option>
              <option value="ignored">Tạm bỏ qua</option>
            </select>

            <div className="relative shrink-0">
              <button
                type="button"
                onClick={() => setExportOpen(open => !open)}
                disabled={exporting}
                aria-haspopup="menu"
                aria-expanded={exportOpen}
                className="flex items-center gap-1 px-3.5 py-1.5 rounded-full bg-white dark:bg-[#1e293b] border border-pink-200 dark:border-pink-900/40 text-[#a43073] dark:text-pink-400 text-xs font-bold hover:bg-pink-50 dark:hover:bg-pink-900/20 disabled:opacity-60"
                title="Xuất các từ đang hiển thị theo bộ lọc"
              >
                <span className="material-symbols-outlined text-[16px]">download</span>
                <span>{exporting ? 'Đang xuất...' : 'Xuất'}</span>
              </button>
              {exportOpen && (
                <div role="menu" className="absolute right-0 top-full mt-1 w-52 bg-white dark:bg-[#1e293b] rounded-2xl shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 py-1.5 z-20">
                  <button role="menuitem" onClick={() => void handleExport('csv')} className="w-full text-left px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-pink-50 dark:hover:bg-slate-700">
                    Tệp CSV (Excel)
                  </button>
                  <button role="menuitem" onClick={() => void handleExport('anki')} className="w-full text-left px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-pink-50 dark:hover:bg-slate-700">
                    Tệp nhập vào Anki
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center justify-between gap-3 rounded-2xl bg-rose-50 dark:bg-rose-900/20 p-4 text-sm text-rose-700 dark:text-rose-400">
            <span>{error}</span>
            <button onClick={reload} className="px-4 py-1.5 rounded-full bg-[#a43073] text-white text-xs font-bold">Thử lại</button>
          </div>
        )}

        {!error && loading && items.length === 0 && <div className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">Đang tải Sổ tay...</div>}

        {!error && !loading && items.length === 0 && (
          <div className="py-10 flex flex-col items-center gap-3 text-center">
            <div className="w-14 h-14 rounded-2xl bg-pink-100 dark:bg-pink-900/30 text-[#a43073] dark:text-pink-400 flex items-center justify-center">
              <span className="material-symbols-outlined text-[30px]">menu_book</span>
            </div>
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{filtersActive ? 'Không có từ nào khớp bộ lọc.' : 'Sổ tay của bạn chưa có từ nào.'}</p>
            {!filtersActive && (
              <>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm">Bấm “+ Sổ tay” cạnh từ vựng khi đọc truyện, mỗi từ sẽ có sẵn ảnh ngữ cảnh và 3 thẻ ôn.</p>
                <button onClick={onNavigateToReader} className="px-5 py-2 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-xs font-bold">Đọc truyện ngay</button>
              </>
            )}
          </div>
        )}

        {items.length > 0 && (
          <div className={`overflow-x-auto w-full custom-scrollbar transition-opacity ${loading ? 'opacity-60' : ''}`}>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#eff4ff] dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-xs font-bold rounded-xl">
                  <th className="py-3 px-4 rounded-l-xl">Hán Tự & Pinyin</th>
                  <th className="py-3 px-4">Âm Hán Việt</th>
                  <th className="py-3 px-4">Nghĩa Tiếng Việt</th>
                  <th className="py-3 px-4">Cấp HSK</th>
                  <th className="py-3 px-4">Nguồn Truyện</th>
                  <th className="py-3 px-4">Trạng Thái</th>
                  <th className="py-3 px-4 text-right rounded-r-xl">Thao Tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700 text-xs">
                {visibleItems.map(item => (
                  <tr key={item.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/60 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => void speakChinese(item.term, 0.85)}
                          className="text-[#a43073] dark:text-pink-400 hover:scale-110 transition-transform"
                          title="Phát âm"
                        >
                          <span className="material-symbols-outlined text-[18px]">volume_up</span>
                        </button>
                        <div className="flex flex-col">
                          <span className="text-base font-bold text-slate-800 dark:text-white font-['Noto_Serif_SC']">{item.term}</span>
                          <span className="font-mono text-blue-600 dark:text-blue-300 text-[11px]">{item.pinyin ?? ''}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-700 dark:text-slate-200">{item.sino_vietnamese ?? '—'}</td>
                    <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300 font-medium max-w-[260px]">
                      <span className="line-clamp-2">{item.meaning_vi ?? '—'}</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-300 text-[11px] font-bold whitespace-nowrap">{hskLabel(item.hsk_level)}</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <button onClick={() => setDetailId(item.id)} className="text-blue-700 dark:text-blue-300 hover:underline flex items-center gap-1 font-medium text-left">
                        {item.first_context?.source_label ?? 'Tra cứu từ điển'}
                        {item.contexts_count > 1 && <span className="text-slate-400 dark:text-slate-500">(+{item.contexts_count - 1})</span>}
                      </button>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-col items-start gap-1">
                        <select
                          value={item.status}
                          disabled={busyId === item.id}
                          onChange={e => void handleStatusChange(item, e.target.value as VocabStatus)}
                          className={`px-2.5 py-0.5 rounded-full font-bold text-[11px] outline-none cursor-pointer border-0 ${STATUS_STYLE[item.status]}`}
                          aria-label={`Trạng thái của ${item.term}`}
                        >
                          {(Object.keys(STATUS_LABEL) as VocabStatus[]).map(status => (
                            <option key={status} value={status}>{STATUS_LABEL[status]}</option>
                          ))}
                        </select>
                        {item.is_due && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 font-bold text-[10px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span> Cần ôn lại
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => void handleToggleStar(item)}
                          disabled={busyId === item.id}
                          className={`p-1 rounded-full ${item.is_starred ? 'text-amber-500' : 'text-slate-400 dark:text-slate-500 hover:text-amber-500 dark:hover:text-amber-400'}`}
                          title="Đánh dấu sao"
                        >
                          <span className="material-symbols-outlined text-[18px]">{item.is_starred ? 'star' : 'star_border'}</span>
                        </button>
                        <button onClick={() => setDetailId(item.id)} className="p-1 rounded-full text-slate-400 dark:text-slate-500 hover:text-[#0060ac] dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20" title="Xem chi tiết, ghi chú, thẻ ôn">
                          <span className="material-symbols-outlined text-[18px]">info</span>
                        </button>
                        <button onClick={() => setDeleteTarget(item)} className="p-1 rounded-full text-slate-400 dark:text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20" title="Xóa từ">
                          <span className="material-symbols-outlined text-[18px]">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {pageCount > 1 && (
          <div className="flex items-center justify-center gap-3 pt-2 text-xs font-semibold text-slate-600 dark:text-slate-300">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-4 py-1.5 rounded-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-40">Trang trước</button>
            <span>Trang {page} / {pageCount}</span>
            <button disabled={page >= pageCount} onClick={() => setPage(page + 1)} className="px-4 py-1.5 rounded-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-40">Trang sau</button>
          </div>
        )}
      </div>

      <DismissedSuggestions showToast={showToast} />

      <VocabDetailModal
        entryId={detailId}
        onClose={() => setDetailId(null)}
        onChanged={() => {
          reload();
          onChanged();
        }}
        onDeleted={() => {
          setDetailId(null);
          reload();
          onChanged();
        }}
        onOpenReader={onOpenReader}
        showToast={showToast}
      />

      {deleteTarget && (
        <ConfirmDialog
          title={`Xóa “${deleteTarget.term}”?`}
          message="Từ cùng mọi ngữ cảnh, thẻ ôn và lịch sử ôn sẽ bị xóa và không thể khôi phục."
          confirmLabel="Xóa từ"
          busy={deleting}
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </>
  );
};
