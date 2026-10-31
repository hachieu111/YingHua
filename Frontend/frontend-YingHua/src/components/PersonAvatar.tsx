import React from 'react';
import { BoardRow } from '../api/gamification';
import { DEFAULT_AVATAR_PRESET, presetAvatarUrl } from '../data/avatarPresets';
import { AvatarFrame } from './AvatarFrame';
import { ProfileAvatar } from './ProfileAvatar';

interface PersonAvatarProps {
  row: BoardRow;
  /** Kích thước ảnh, ví dụ `w-10 h-10`. */
  sizeClass: string;
}

/** Avatar của một dòng bảng xếp hạng: ảnh thật, ảnh gợi ý hoặc biểu tượng ẩn danh, kèm khung và dấu VIP. */
export const PersonAvatar: React.FC<PersonAvatarProps> = ({ row, sizeClass }) => {
  if (row.anonymous) {
    return (
      <span className={`${sizeClass} rounded-full bg-slate-200 text-slate-500 flex items-center justify-center shrink-0 dark:bg-slate-700 dark:text-slate-400`} title="Người học ẩn danh">
        <span className="material-symbols-outlined text-[60%]">person</span>
      </span>
    );
  }
  return (
    <AvatarFrame styleKey={row.frame?.style_key} isVip={row.is_vip}>
      <ProfileAvatar
        serverUrl={row.avatar_url}
        fallbackSrc={presetAvatarUrl(row.avatar_preset) ?? presetAvatarUrl(DEFAULT_AVATAR_PRESET) ?? ''}
        alt={row.display_name}
        className={`${sizeClass} rounded-full object-cover bg-white dark:bg-slate-800`}
      />
    </AvatarFrame>
  );
};
