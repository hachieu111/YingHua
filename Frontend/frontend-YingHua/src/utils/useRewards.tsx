import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { GamificationMe, getMyGamification } from '../api/gamification';
import { Wallet, getWallet } from '../api/rewards';
import { ACTIVITY_EVENT } from './useStreak';

/** Phát ra sau khi ví hoặc huy hiệu/khung thay đổi (đổi thưởng, mở khóa, đeo huy hiệu...) để mọi màn đọc lại từ máy chủ. */
export const REWARDS_EVENT = 'yinghua:rewards';

export const notifyRewardsChanged = (): void => {
  window.dispatchEvent(new Event(REWARDS_EVENT));
};

interface RewardsState {
  /** Ví xu/vé, VIP và khung đang đeo; null khi chưa đăng nhập hoặc chưa tải được. */
  wallet: Wallet | null;
  /** XP hôm nay, hạng mùa và huy hiệu đang đeo; null khi chưa đăng nhập hoặc chưa tải được. */
  me: GamificationMe | null;
  loading: boolean;
  error: boolean;
  reload: () => void;
}

const RewardsContext = createContext<RewardsState>({
  wallet: null,
  me: null,
  loading: false,
  error: false,
  reload: () => undefined
});

/** Ví và XP của người dùng, lấy từ máy chủ; tải lại khi quay lại tab, sau mỗi hoạt động học và sau khi ví đổi. */
export const RewardsProvider: React.FC<{ isLoggedIn: boolean; children: React.ReactNode }> = ({ isLoggedIn, children }) => {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [me, setMe] = useState<GamificationMe | null>(null);
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
    window.addEventListener(REWARDS_EVENT, reload);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener(ACTIVITY_EVENT, reload);
      window.removeEventListener(REWARDS_EVENT, reload);
    };
  }, [isLoggedIn, reload]);

  useEffect(() => {
    if (!isLoggedIn) {
      setWallet(null);
      setMe(null);
      setError(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    Promise.allSettled([getWallet(controller.signal), getMyGamification(controller.signal)]).then(([walletResult, meResult]) => {
      if (controller.signal.aborted) return;
      if (walletResult.status === 'fulfilled') setWallet(walletResult.value);
      if (meResult.status === 'fulfilled') setMe(meResult.value);
      setError(walletResult.status === 'rejected' || meResult.status === 'rejected');
      setLoading(false);
    });
    return () => controller.abort();
  }, [isLoggedIn, tick]);

  const value = useMemo(() => ({ wallet, me, loading, error, reload }), [wallet, me, loading, error, reload]);
  return <RewardsContext.Provider value={value}>{children}</RewardsContext.Provider>;
};

export const useRewards = (): RewardsState => useContext(RewardsContext);
