import React from 'react';
import { Badge } from '../api/gamification';
import { badgeStyle, tierLabel } from '../data/achievements';

interface BadgeChipProps {
  badge: Badge;
  /** Hiện thêm cấp (I, II...) sau tên. */
  showTier?: boolean;
  className?: string;
}

/** Viên huy hiệu đang đeo: màu và biểu tượng theo `style_key` của máy chủ. */
export const BadgeChip: React.FC<BadgeChipProps> = ({ badge, showTier = false, className = '' }) => {
  const style = badgeStyle(badge.style_key);
  const Icon = style.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border shadow-xs ${style.color} ${className}`}>
      <Icon className="w-3.5 h-3.5" strokeWidth={2.2} aria-hidden="true" />
      <span className="text-[11px] font-bold tracking-wide uppercase">{badge.name}</span>
      {showTier && <span className="text-[10px] font-bold opacity-80">{tierLabel(badge.tier)}</span>}
    </span>
  );
};
