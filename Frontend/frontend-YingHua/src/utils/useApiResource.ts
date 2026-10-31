import { DependencyList, useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { REWARDS_EVENT } from './useRewards';
import { ACTIVITY_EVENT } from './useStreak';

interface ApiResource<T> {
  data: T | null;
  /** true khi chưa có dữ liệu nào và đang tải lần đầu (các lần tải lại nền không bật cờ này). */
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Tải một tài nguyên từ API, giữ dữ liệu cũ khi tải lại nền. Tự đọc lại khi quay lại tab và sau mỗi hoạt động học / thay đổi ví,
 * để dấu hiệu trên màn hình luôn khớp máy chủ. `enabled=false` thì không gọi API (vd. chưa đăng nhập).
 */
export function useApiResource<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList,
  enabled = true
): ApiResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  // Cập nhật trong effect (khai báo trước effect tải) để không ghi vào ref trong lúc render.
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    if (!enabled) return;
    const refresh = () => {
      if (document.visibilityState === 'visible') reload();
    };
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener(ACTIVITY_EVENT, reload);
    window.addEventListener(REWARDS_EVENT, reload);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener(ACTIVITY_EVENT, reload);
      window.removeEventListener(REWARDS_EVENT, reload);
    };
  }, [enabled, reload]);

  // Đổi tham số (kỳ, chỉ số, trang...) thì bỏ dữ liệu cũ để không hiện nhầm.
  useEffect(() => {
    setData(null);
    setError(null);
    setLoading(enabled);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    fetcherRef
      .current(controller.signal)
      .then(value => {
        setData(value);
        setError(null);
      })
      .catch(err => {
        if (!isAbortedError(err)) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, tick, ...deps]);

  return { data, loading, error, reload };
}
