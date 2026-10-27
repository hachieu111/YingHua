import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { StreakReport, getStreak } from '../api/stats';

/** Phát ra sau khi người học ôn thẻ hoặc đọc trang để chuỗi ngày học được tải lại từ máy chủ (F12.02). */
export const ACTIVITY_EVENT = 'yinghua:activity';

export const notifyActivity = (): void => {
  window.dispatchEvent(new Event(ACTIVITY_EVENT));
};

interface StreakState {
  /** null khi chưa đăng nhập hoặc chưa tải được. */
  streak: StreakReport | null;
  loading: boolean;
  error: boolean;
  reload: () => void;
}

const StreakContext = createContext<StreakState>({ streak: null, loading: false, error: false, reload: () => undefined });

/** Chuỗi ngày học lấy từ máy chủ; tải lại khi quay lại tab và sau mỗi hoạt động học. */
export const StreakProvider: React.FC<{ isLoggedIn: boolean; children: React.ReactNode }> = ({ isLoggedIn, children }) => {
  const [streak, setStreak] = useState<StreakReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick(value => value + 1), []);

  useEffect(() => {
    if (!isLoggedIn) return;
    const refresh = () => {
      if (document.visibilityState === 'visible') reload();
    };
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener(ACTIVITY_EVENT, reload);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener(ACTIVITY_EVENT, reload);
    };
  }, [isLoggedIn, reload]);

  useEffect(() => {
    if (!isLoggedIn) {
      setStreak(null);
      setError(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    getStreak(controller.signal)
      .then(report => {
        setStreak(report);
        setError(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [isLoggedIn, tick]);

  const value = useMemo(() => ({ streak, loading, error, reload }), [streak, loading, error, reload]);
  return <StreakContext.Provider value={value}>{children}</StreakContext.Provider>;
};

export const useStreak = (): StreakState => useContext(StreakContext);
