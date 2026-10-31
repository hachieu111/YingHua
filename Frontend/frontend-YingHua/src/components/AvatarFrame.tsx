import React from 'react';

/** Viền khung avatar theo `style_key` do máy chủ trả (M17); khóa lạ dùng viền mặc định. */
const FRAME_STYLES: Record<string, string> = {
  sakura_gold: 'ring-[3px] ring-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.75)]',
  spring_petal: 'ring-[3px] ring-pink-300 shadow-[0_0_10px_rgba(244,114,182,0.5)]',
  vip_sakura: 'ring-[3px] ring-[#a43073] shadow-[0_0_12px_rgba(164,48,115,0.55)]',
  bamboo_leaf: 'ring-[3px] ring-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.45)]',
  ink_cloud: 'ring-[3px] ring-slate-700 shadow-[0_0_10px_rgba(51,65,85,0.5)]'
};

const DEFAULT_FRAME = 'ring-[3px] ring-pink-200';

export const frameClass = (styleKey: string | null | undefined): string =>
  styleKey ? (FRAME_STYLES[styleKey] ?? DEFAULT_FRAME) : '';

interface AvatarFrameProps {
  /** `style_key` của khung đang đeo; null = không đeo khung. */
  styleKey?: string | null;
  isVip?: boolean;
  className?: string;
  children: React.ReactNode;
}

/** Bọc avatar bằng khung đang đeo và dấu VIP nhỏ ở góc. */
export const AvatarFrame: React.FC<AvatarFrameProps> = ({ styleKey, isVip = false, className = '', children }) => (
  <span className={`relative inline-flex shrink-0 rounded-full ${frameClass(styleKey)} ${className}`}>
    {children}
    {isVip && (
      <span
        className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-amber-400 text-amber-950 flex items-center justify-center shadow-xs"
        title="Thành viên VIP"
      >
        <span className="material-symbols-outlined text-[11px]" style={{ fontVariationSettings: "'FILL' 1" }}>
          workspace_premium
        </span>
      </span>
    )}
  </span>
);

/** Viên "VIP" dùng trên thẻ truyện, danh sách chương, bảng xếp hạng. */
export const VipPill: React.FC<{ className?: string; label?: string }> = ({ className = '', label = 'VIP' }) => (
  <span
    className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-300 to-amber-400 text-amber-950 text-[10px] font-extrabold shadow-xs ${className}`}
  >
    <span className="material-symbols-outlined text-[12px]" style={{ fontVariationSettings: "'FILL' 1" }}>
      workspace_premium
    </span>
    {label}
  </span>
);
