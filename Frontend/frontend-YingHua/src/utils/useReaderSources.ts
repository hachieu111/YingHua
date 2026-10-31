import { useCallback, useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { ApiChapter, ApiPage, ApiSeries, getSeries, listQuickUploads, listSeries, pickReadTarget } from '../api/library';
import { ReaderTarget } from '../types';

/** Số truyện/ảnh tối đa lấy một lần cho bộ chọn nguồn đọc (giới hạn trang của máy chủ). */
const SOURCE_PAGE_SIZE = 100;

export interface ReaderSources {
  /** Truyện riêng tư của người dùng; null khi chưa tải xong hoặc chưa đăng nhập. */
  series: ApiSeries[] | null;
  /** Ảnh tải nhanh còn hạn, cũ → mới; null khi chưa tải xong hoặc chưa đăng nhập. */
  quick: ApiPage[] | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Nguồn đọc của người dùng (truyện riêng tư + ảnh tải nhanh) lấy từ máy chủ.
 * Tải khi vào, khi `refreshKey` đổi (vừa tải ảnh lên) và khi quay lại tab.
 */
export function useReaderSources(enabled: boolean, refreshKey: number): ReaderSources {
  const [series, setSeries] = useState<ApiSeries[] | null>(null);
  const [quick, setQuick] = useState<ApiPage[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    if (!enabled) {
      setSeries(null);
      setQuick(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    Promise.allSettled([
      listSeries({ scope: 'mine', size: SOURCE_PAGE_SIZE }, controller.signal),
      listQuickUploads(1, SOURCE_PAGE_SIZE, controller.signal)
    ]).then(([seriesResult, quickResult]) => {
      if (controller.signal.aborted) return;
      if (seriesResult.status === 'fulfilled') setSeries(seriesResult.value.items);
      if (quickResult.status === 'fulfilled') setQuick([...quickResult.value.items].sort((a, b) => a.id - b.id));
      const failure = [seriesResult, quickResult].find(result => result.status === 'rejected');
      setError(failure && failure.status === 'rejected' && !isAbortedError(failure.reason) ? errorMessage(failure.reason) : null);
      setLoading(false);
    });
    return () => controller.abort();
  }, [enabled, refreshKey, tick]);

  useEffect(() => {
    if (!enabled) return;
    const onVisible = () => {
      if (!document.hidden) reload();
    };
    window.addEventListener('focus', onVisible);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.removeEventListener('focus', onVisible);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [enabled, reload]);

  return { series, quick, loading, error, reload };
}

/** Mở một truyện riêng tư: đọc tiếp chương đang dở, hoặc chương đầu có trang. */
export function useOpenSeries(onOpenReader: (target: ReaderTarget) => void) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const openSeries = useCallback(
    async (series: ApiSeries): Promise<boolean> => {
      setMessage(null);
      const resume = series.progress;
      if (resume && resume.chapter_id !== null && !resume.completed) {
        onOpenReader({ chapterId: resume.chapter_id, pageNo: resume.page_no ?? undefined, pageId: resume.page_id ?? undefined });
        return true;
      }
      setBusyId(series.id);
      try {
        const target = pickReadTarget(await getSeries(series.id));
        if (target) {
          onOpenReader(target);
          return true;
        }
        setMessage('Truyện này chưa có trang nào để đọc.');
        return false;
      } catch (err) {
        setMessage(errorMessage(err));
        return false;
      } finally {
        setBusyId(null);
      }
    },
    [onOpenReader]
  );

  return { openSeries, busyId, message };
}

/** Các chương đọc được của một truyện (đã sắp theo số chương); Khách chỉ thấy chương đọc thử. */
export function useSeriesChapters(seriesId: number | null, isLoggedIn: boolean, refreshKey: number): ApiChapter[] {
  const [chapters, setChapters] = useState<ApiChapter[]>([]);

  useEffect(() => {
    setChapters([]);
    if (seriesId === null) return;
    const controller = new AbortController();
    getSeries(seriesId, controller.signal)
      .then(detail => {
        const readable = detail.chapters.filter(chapter => chapter.page_count > 0 && (isLoggedIn || chapter.is_trial));
        setChapters(readable.sort((a, b) => a.number - b.number));
      })
      .catch(() => {
        // Không tải được danh sách chương thì chỉ ẩn ô chọn chương, vẫn đọc được chương đang mở.
      });
    return () => controller.abort();
  }, [seriesId, isLoggedIn, refreshKey]);

  return chapters;
}
