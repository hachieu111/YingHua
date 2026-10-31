import React, { useEffect, useState } from 'react';
import { CurrentSeason, SeasonResult, SeasonTier, TIER_LABEL, getCurrentSeason, listAchievements, listMySeasons } from '../api/gamification';
import { listFrames } from '../api/rewards';
import { useApiResource } from '../utils/useApiResource';

const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;
const SECONDS_PER_DAY = 86400;

/**
 * Số giây còn lại của mùa. Mốc là `seconds_left` do máy chủ tính; phần trôi qua đo bằng đồng hồ đơn điệu
 * (performance.now) nên đổi giờ trên máy không làm sai kết quả.
 */
function useSeasonCountdown(season: CurrentSeason | null, onExpire: () => void): number | null {
  const [left, setLeft] = useState<number | null>(null);

  useEffect(() => {
    if (!season) {
      setLeft(null);
      return;
    }
    const startedAt = performance.now();
    let expired = false;
    const update = () => {
      const remaining = Math.max(0, season.seconds_left - Math.floor((performance.now() - startedAt) / 1000));
      setLeft(remaining);
      if (remaining === 0 && !expired) {
        expired = true;
        onExpire();
      }
    };
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
    // `onExpire` ổn định theo reload của useApiResource; chỉ đặt lại mốc khi máy chủ trả mùa mới.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season]);

  return left;
}

export const formatCountdown = (seconds: number): string => {
  const days = Math.floor(seconds / SECONDS_PER_DAY);
  const hours = Math.floor((seconds % SECONDS_PER_DAY) / SECONDS_PER_HOUR);
  const minutes = Math.floor((seconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
  if (days > 0) return `${days} ngày ${hours} giờ`;
  if (hours > 0) return `${hours} giờ ${minutes} phút`;
  return `${minutes} phút ${seconds % SECONDS_PER_MINUTE} giây`;
};

interface SeasonState {
  season: CurrentSeason | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Mùa thi đua hiện hành, tự đọc lại khi quay lại tab. */
export function useCurrentSeason(enabled: boolean): SeasonState {
  const { data, loading, error, reload } = useApiResource(signal => getCurrentSeason(signal), [], enabled);
  return { season: data, loading, error, reload };
}

interface SeasonBannerProps {
  state: SeasonState;
}

/** Hai viên đầu trang: số mùa và đồng hồ đếm ngược theo giờ máy chủ. */
export const SeasonBanner: React.FC<SeasonBannerProps> = ({ state }) => {
  const { season, loading, error, reload } = state;
  const left = useSeasonCountdown(season, reload);
  if (loading) return <span className="text-xs text-slate-400">Đang tải mùa thi đua...</span>;
  if (error || !season) {
    return (
      <button type="button" onClick={reload} className="text-xs font-semibold text-rose-600 hover:underline dark:text-rose-400">
        {error ?? 'Không tải được mùa thi đua'} · Thử lại
      </button>
    );
  }
  const finalizing = season.status !== 'active' || season.finalizing_previous || left === 0;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ffd8e7] text-[#85145a] font-bold text-xs shadow-xs dark:text-pink-300 dark:bg-pink-900/40">
        <span>🌸</span> Mùa Đua Top Hoa Anh Đào • Kỳ {season.number}
      </span>
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-bold text-xs dark:bg-amber-900/30 dark:text-amber-300">
        <span className="material-symbols-outlined text-[15px]">timer</span>
        <span>{finalizing ? 'Đang tổng kết mùa' : left !== null ? `Còn ${formatCountdown(left)}` : '—'}</span>
      </span>
    </div>
  );
};

const TIER_ICON: Record<SeasonTier['tier'], { icon: string; box: string }> = {
  top3: { icon: '🥇', box: 'bg-amber-200 text-amber-950 dark:bg-amber-900/40' },
  top10: { icon: '🥈', box: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100' },
  top50: { icon: '🎖️', box: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' }
};

/** Tên khung/huy hiệu tra theo mã từ máy chủ; chưa tải được thì hiện mã. */
interface NameLookup {
  frame: (code: string) => string;
  badge: (code: string) => string;
}

const rewardLines = (tier: SeasonTier, names: NameLookup): string[] => {
  const lines: string[] = [];
  if (tier.frame_code) lines.push(`Khung avatar "${names.frame(tier.frame_code)}"`);
  if (tier.vip_days > 0) lines.push(`${tier.vip_days} ngày VIP`);
  if (tier.tickets > 0) lines.push(`${tier.tickets} vé đọc truyện VIP`);
  if (tier.coins > 0) lines.push(`${tier.coins.toLocaleString('vi-VN')} xu dùng ở cửa hàng đổi thưởng`);
  if (tier.badge_code) lines.push(`Huy hiệu "${names.badge(tier.badge_code)}"`);
  return lines;
};

/** Các bậc thưởng của mùa và bậc bạn đang ở (nếu mùa chốt lúc này). */
export const SeasonRewardsCard: React.FC<SeasonBannerProps> = ({ state }) => {
  const { season, loading, error, reload } = state;
  const frames = useApiResource(signal => listFrames(signal), []);
  const achievements = useApiResource(signal => listAchievements(signal), []);
  const names: NameLookup = {
    frame: code => frames.data?.find(frame => frame.code === code)?.name ?? code,
    badge: code => achievements.data?.find(item => item.code === code)?.name ?? code
  };
  return (
    <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100 relative overflow-hidden dark:bg-slate-800 dark:border-pink-900/40">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#a43073] text-[22px] dark:text-pink-400">card_giftcard</span>
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Phần Thưởng Mùa Giải</h3>
        </div>
        {season && <span className="px-2.5 py-0.5 rounded-full bg-pink-100 text-[#a43073] text-[11px] font-bold dark:bg-pink-900/30 dark:text-pink-400">Kỳ {season.number}</span>}
      </div>

      {loading && <p className="text-xs text-slate-400">Đang tải phần thưởng...</p>}
      {error && !season && (
        <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {error}{' '}
          <button type="button" onClick={reload} className="font-bold underline">
            Thử lại
          </button>
        </p>
      )}
      {season && (
        <>
          <p className="text-xs text-slate-500 mb-4 leading-relaxed dark:text-slate-400">
            Hạng theo XP của cả mùa. Cần ít nhất <strong className="text-[#a43073] dark:text-pink-400">{season.min_xp.toLocaleString('vi-VN')} XP</strong> để được tính thưởng.
            {season.my_rank !== null
              ? ` Hiện bạn đứng hạng ${season.my_rank} với ${season.my_xp.toLocaleString('vi-VN')} XP.`
              : ` Bạn có ${season.my_xp.toLocaleString('vi-VN')} XP trong mùa này.`}
          </p>
          <div className="flex flex-col gap-3">
            {season.tiers.map(tier => {
              const look = TIER_ICON[tier.tier];
              const mine = season.my_tier === tier.tier;
              return (
                <div key={tier.tier} className={`flex items-start gap-3 p-3 rounded-2xl ${mine ? 'bg-pink-50 dark:bg-pink-900/30 ring-2 ring-[#a43073]/40 dark:text-slate-100' : 'bg-[#eff4ff] dark:bg-[#1e293b]'}`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0 ${look.box}`}>{look.icon}</div>
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-100">
                        {tier.rank_from === tier.rank_to ? `Top ${tier.rank_from}` : `Top ${tier.rank_from} ~ ${tier.rank_to}`}
                      </span>
                      {mine && <span className="px-1.5 py-0.5 rounded bg-[#a43073] text-white text-[10px] font-bold">Có bạn!</span>}
                    </div>
                    <ul className="text-[11px] text-slate-600 mt-1 space-y-0.5 dark:text-slate-300">
                      {rewardLines(tier, names).map(line => (
                        <li key={line} className="flex items-start gap-1">
                          <span className="text-[#a43073] dark:text-pink-400">✓</span> {line}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

const formatDate = (iso: string): string => new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });

const HistoryRow: React.FC<{ item: SeasonResult }> = ({ item }) => (
  <li className="flex items-center justify-between gap-3 py-2.5">
    <div className="min-w-0">
      <div className="text-xs font-bold text-slate-800 dark:text-slate-100">Kỳ {item.season_number}</div>
      <div className="text-[10px] text-slate-400">
        {formatDate(item.starts_at)} – {formatDate(item.ends_at)}
      </div>
    </div>
    <div className="text-right shrink-0">
      <div className="text-xs font-bold text-[#a43073] dark:text-pink-400">
        Hạng {item.rank} · {item.xp.toLocaleString('vi-VN')} XP
      </div>
      <div className="text-[10px] text-slate-500 dark:text-slate-400">
        {TIER_LABEL[item.tier]} · {item.reward_granted_at ? 'Đã nhận thưởng' : 'Đang chờ trao thưởng'}
      </div>
    </div>
  </li>
);

/** Kết quả các mùa đã chốt của bạn (F16.09). */
export const SeasonHistoryCard: React.FC<{ enabled: boolean }> = ({ enabled }) => {
  const { data, loading, error, reload } = useApiResource(signal => listMySeasons(1, 10, signal), [], enabled);
  return (
    <div className="rounded-3xl bg-white p-6 shadow-soft border border-pink-100 dark:bg-slate-800 dark:border-pink-900/40">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-[#0060ac] text-[22px] dark:text-blue-300">history</span>
        <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Lịch Sử Mùa Giải</h3>
      </div>
      {loading && <p className="text-xs text-slate-400">Đang tải...</p>}
      {error && (
        <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
          {error}{' '}
          <button type="button" onClick={reload} className="font-bold underline">
            Thử lại
          </button>
        </p>
      )}
      {data && data.items.length === 0 && <p className="text-xs text-slate-500 dark:text-slate-400">Bạn chưa có mùa nào đã chốt. Tích XP để có tên trong bảng vàng mùa tới!</p>}
      {data && data.items.length > 0 && (
        <ul className="divide-y divide-slate-100 dark:divide-slate-700">
          {data.items.map(item => (
            <HistoryRow key={item.season_number} item={item} />
          ))}
        </ul>
      )}
    </div>
  );
};
