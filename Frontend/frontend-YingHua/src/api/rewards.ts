// Gọi API VIP & Phần thưởng (M17): ví xu/vé, cửa hàng đổi thưởng, khung avatar, mở khóa truyện VIP và phần quản trị.
import { apiRequest } from './client';
import { FrameInfo } from './gamification';
import { Paged } from './library';

export interface VipStatus {
  is_active: boolean;
  vip_until: string | null;
  days_left: number;
}

export interface Wallet {
  coin_balance: number;
  ticket_balance: number;
  vip: VipStatus;
  equipped_frame: FrameInfo | null;
}

export type Currency = 'coin' | 'ticket' | 'vip_days';

export interface LedgerEntry {
  id: number;
  currency: Currency;
  /** Dương là nhận, âm là tiêu hoặc thu. */
  amount: number;
  balance_after: number | null;
  vip_until_after: string | null;
  reason: string;
  reason_label: string;
  note: string | null;
  created_at: string;
}

export interface AiLimits {
  quiz_daily_llm_limit: number;
  ai_note_daily_limit: number;
  grammar_daily_limit: number;
  mistake_review_daily_limit: number;
}

export interface VipOverview extends VipStatus {
  ai_limits: AiLimits;
  can_read_vip_series: boolean;
  can_use_vip_frame: boolean;
  unlocked_series_count: number;
}

export interface UnlockResult {
  series_id: number;
  unlocked_at: string;
  tickets_left: number;
}

export interface UnlockItem {
  series_id: number;
  series_title: string | null;
  unlocked_at: string;
  source: string;
}

export type ItemKind = 'vip_days' | 'vip_ticket' | 'avatar_frame';

export interface ShopItem {
  id: number;
  code: string;
  name: string;
  description: string | null;
  kind: ItemKind;
  price_coins: number;
  vip_days: number | null;
  ticket_count: number | null;
  frame: FrameInfo | null;
  per_user_limit: number | null;
  /** Số lượt đổi còn lại của người gọi; null = không giới hạn. */
  remaining: number | null;
  owned: boolean;
  affordable: boolean;
}

export interface Redemption {
  id: number;
  item_id: number;
  item_code: string;
  item_name: string;
  price_coins: number;
  created_at: string;
  wallet: Wallet;
}

export interface FrameEntry {
  code: string;
  name: string;
  description: string | null;
  style_key: string;
  acquire_kind: string;
  acquire_label: string;
  owned: boolean;
  expires_at: string | null;
  equippable: boolean;
  equipped: boolean;
}

export interface SeriesVipResult {
  series_id: number;
  is_vip: boolean;
  has_trial_chapter: boolean;
  warning: string | null;
}

export interface AdminRewardItem {
  id: number;
  code: string;
  name: string;
  description: string | null;
  kind: ItemKind;
  price_coins: number;
  vip_days: number | null;
  ticket_count: number | null;
  frame: FrameInfo | null;
  per_user_limit: number | null;
  is_active: boolean;
  sort_order: number;
  /** Đã có lượt đổi: không đổi được loại và đối tượng. */
  has_redemptions: boolean;
  updated_at: string;
}

export interface RewardItemInput {
  name: string;
  description: string | null;
  price_coins: number;
  vip_days: number | null;
  ticket_count: number | null;
  frame_code: string | null;
  per_user_limit: number | null;
  is_active: boolean;
  sort_order: number;
}

export interface AdminLedgerEntry extends LedgerEntry {
  actor_id: number | null;
}

export interface AdminUserRewards {
  wallet: Wallet;
  unlocks: UnlockItem[];
  frames: { code: string; name: string; source: string; acquired_at: string; expires_at: string | null }[];
  ledger: Paged<AdminLedgerEntry>;
}

/** Giới hạn khớp máy chủ để kiểm tra nhanh ở form; máy chủ vẫn là nơi quyết định. */
export const NOTE_MAX_LENGTH = 500;
export const MAX_COINS_PER_GRANT = 100_000;
export const MAX_TICKETS_PER_GRANT = 10;
export const MAX_VIP_DAYS_PER_GRANT = 365;

/** UUID do trình duyệt sinh mỗi lần bấm, để máy chủ bỏ qua yêu cầu lặp (bấm đúp). */
export const newRequestId = (): string => crypto.randomUUID();

export const getWallet = (signal?: AbortSignal): Promise<Wallet> => apiRequest<Wallet>('/rewards/wallet', { signal });

export const listLedger = (
  query: { currency?: Currency; page?: number; size?: number },
  signal?: AbortSignal
): Promise<Paged<LedgerEntry>> => {
  const params = new URLSearchParams({ page: String(query.page ?? 1), size: String(query.size ?? 20) });
  if (query.currency) params.set('currency', query.currency);
  return apiRequest<Paged<LedgerEntry>>(`/rewards/wallet/ledger?${params.toString()}`, { signal });
};

export const listShopItems = (signal?: AbortSignal): Promise<ShopItem[]> =>
  apiRequest<ShopItem[]>('/rewards/shop/items', { signal });

export const redeemItem = (itemId: number, requestId: string): Promise<Redemption> =>
  apiRequest<Redemption>('/rewards/redemptions', { method: 'POST', body: { item_id: itemId, request_id: requestId } });

export const listFrames = (signal?: AbortSignal): Promise<FrameEntry[]> =>
  apiRequest<FrameEntry[]>('/rewards/frames', { signal });

/** Đeo khung avatar; truyền null để tháo. */
export const equipFrame = (frameCode: string | null): Promise<{ equipped_frame: FrameInfo | null }> =>
  apiRequest('/rewards/frames/equipped', { method: 'PUT', body: { frame_code: frameCode } });

export const getVipOverview = (signal?: AbortSignal): Promise<VipOverview> =>
  apiRequest<VipOverview>('/vip/me', { signal });

export const unlockSeries = (seriesId: number, requestId: string): Promise<UnlockResult> =>
  apiRequest<UnlockResult>('/vip/unlocks', { method: 'POST', body: { series_id: seriesId, request_id: requestId } });

export const listUnlocks = (signal?: AbortSignal): Promise<UnlockItem[]> =>
  apiRequest<UnlockItem[]>('/vip/unlocks', { signal });

// --- Quản trị ---

export const setSeriesVip = (seriesId: number, isVip: boolean): Promise<SeriesVipResult> =>
  apiRequest<SeriesVipResult>(`/admin/series/${seriesId}/vip`, { method: 'PUT', body: { is_vip: isVip } });

export const listAdminRewardItems = (signal?: AbortSignal): Promise<AdminRewardItem[]> =>
  apiRequest<AdminRewardItem[]>('/admin/reward-items', { signal });

export const createRewardItem = (
  input: RewardItemInput & { code: string; kind: ItemKind }
): Promise<AdminRewardItem> => apiRequest<AdminRewardItem>('/admin/reward-items', { method: 'POST', body: input });

export const updateRewardItem = (itemId: number, changes: Partial<RewardItemInput>): Promise<AdminRewardItem> =>
  apiRequest<AdminRewardItem>(`/admin/reward-items/${itemId}`, { method: 'PATCH', body: changes });

export const getUserRewards = (userId: number, page = 1, size = 20, signal?: AbortSignal): Promise<AdminUserRewards> =>
  apiRequest<AdminUserRewards>(`/admin/users/${userId}/rewards?page=${page}&size=${size}`, { signal });

/** Cấp thêm `days` ngày VIP, hoặc thu hồi toàn bộ VIP (`revoke`); luôn kèm lý do. */
export const grantVip = (
  userId: number,
  body: { days?: number; revoke?: boolean; reason: string; request_id: string }
): Promise<Wallet> =>
  apiRequest<Wallet>(`/admin/users/${userId}/vip-grants`, { method: 'POST', body });

export const adjustWallet = (
  userId: number,
  body: { currency: 'coin' | 'ticket'; amount: number; reason: string; request_id: string }
): Promise<Wallet> => apiRequest<Wallet>(`/admin/users/${userId}/wallet-adjustments`, { method: 'POST', body });

export interface AdminFrame {
  id: number;
  code: string;
  name: string;
  description: string | null;
  style_key: string;
  acquire_kind: string;
  acquire_label: string;
}

/** Danh sách khung cho form món đổi thưởng; chỉ khung `acquire_kind === 'shop'` được bán. */
export const listAdminFrames = (signal?: AbortSignal): Promise<AdminFrame[]> =>
  apiRequest<AdminFrame[]>('/admin/avatar-frames', { signal });
