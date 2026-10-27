import { useEffect, useState } from 'react';
import { ActivityReport, LearningOverview, getActivity, getOverview } from '../api/stats';
import { ACTIVITY_EVENT } from './useStreak';

export const ACTIVITY_DAYS = 14;

export interface LearningStats {
  overview: LearningOverview | null;
  activity: ActivityReport | null;
  loading: boolean;
  error: boolean;
  reload: () => void;
}

/** Thống kê học tập từ máy chủ (F12.01); tải lại khi quay lại tab và sau mỗi hoạt động học. */
export function useLearningStats(): LearningStats {
  const [overview, setOverview] = useState<LearningOverview | null>(null);
  const [activity, setActivity] = useState<ActivityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === 'visible') setTick(value => value + 1);
    };
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener(ACTIVITY_EVENT, refresh);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener(ACTIVITY_EVENT, refresh);
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([getOverview(controller.signal), getActivity(ACTIVITY_DAYS, controller.signal)])
      .then(([nextOverview, nextActivity]) => {
        setOverview(nextOverview);
        setActivity(nextActivity);
        setError(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tick]);

  return { overview, activity, loading, error, reload: () => setTick(value => value + 1) };
}
