import {
  Crown,
  Flower2,
  Moon,
  ScrollText,
  Sprout,
  Star,
  Trophy,
  type LucideIcon
} from 'lucide-react';

/** Giao diện của huy hiệu theo `style_key` do máy chủ trả; tên, mô tả, ngưỡng và tiến độ đều lấy từ API. */
export interface BadgeStyle {
  color: string;
  icon: LucideIcon;
}

const BADGE_STYLES: Record<string, BadgeStyle> = {
  flower: { color: 'bg-[#ffd8e7] text-[#85145a] border-pink-300', icon: Flower2 },
  crown: { color: 'bg-amber-100 text-amber-950 border-amber-300', icon: Crown },
  star: { color: 'bg-blue-100 text-blue-900 border-blue-300', icon: Star },
  sprout: { color: 'bg-emerald-100 text-emerald-900 border-emerald-300', icon: Sprout },
  trophy: { color: 'bg-purple-100 text-purple-900 border-purple-300', icon: Trophy },
  moon: { color: 'bg-indigo-100 text-indigo-900 border-indigo-300', icon: Moon },
  scroll: { color: 'bg-rose-100 text-rose-900 border-rose-300', icon: ScrollText }
};

const FALLBACK_STYLE: BadgeStyle = { color: 'bg-slate-100 text-slate-800 border-slate-300', icon: Star };

export const badgeStyle = (styleKey: string | null | undefined): BadgeStyle =>
  (styleKey ? BADGE_STYLES[styleKey] : undefined) ?? FALLBACK_STYLE;

const ROMAN = ['', 'I', 'II', 'III', 'IV', 'V'];

/** Cấp huy hiệu dạng chữ La Mã (cấp 0 = chưa mở khóa). */
export const tierLabel = (tier: number): string => (tier > 0 ? `Cấp ${ROMAN[tier] ?? tier}` : 'Chưa mở khóa');
