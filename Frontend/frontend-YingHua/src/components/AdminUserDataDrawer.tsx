import React, { useEffect, useState } from 'react';
import { AdminUser } from '../api/adminUsers';
import { AdminUserCardsTab } from './AdminUserCardsTab';
import { AdminUserLibraryTab } from './AdminUserLibraryTab';
import { AdminUserOverviewTab } from './AdminUserOverviewTab';
import { AdminUserRewardsTab } from './AdminUserRewardsTab';
import { AdminUserSettingsTab } from './AdminUserSettingsTab';
import { AdminUserVocabTab } from './AdminUserVocabTab';

interface AdminUserDataDrawerProps {
  user: AdminUser;
  onClose: () => void;
  notify: (message: string) => void;
}

type TabKey = 'overview' | 'vocab' | 'cards' | 'settings' | 'library' | 'rewards';

const TABS: [TabKey, string][] = [
  ['overview', 'Tổng quan'],
  ['vocab', 'Sổ tay'],
  ['cards', 'Thẻ ôn'],
  ['settings', 'Cài đặt'],
  ['library', 'Thư viện & đọc'],
  ['rewards', 'Ví & VIP']
];

/** Ngăn kéo xem/sửa toàn bộ dữ liệu của một người dùng (F13.07, US-QT-14). */
export const AdminUserDataDrawer: React.FC<AdminUserDataDrawerProps> = ({ user, onClose, notify }) => {
  const [tab, setTab] = useState<TabKey>('overview');

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[60] bg-slate-900/40 dark:bg-black/70 backdrop-blur-sm flex justify-end" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Dữ liệu của ${user.display_name}`}
        className="bg-white dark:bg-[#0f172a] text-slate-800 dark:text-slate-200 w-full max-w-3xl h-full shadow-2xl dark:shadow-none dark:border-l dark:border-slate-700 flex flex-col transition-colors duration-300"
        onClick={event => event.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 p-5 border-b border-slate-100 dark:border-slate-700">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans'] truncate">Dữ liệu của {user.display_name}</h2>
            <div className="text-xs text-slate-500 dark:text-slate-400 truncate">{user.email}</div>
          </div>
          <button onClick={onClose} aria-label="Đóng" className="material-symbols-outlined text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white">close</button>
        </header>
        <div role="status" className="mx-5 mt-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/50 px-3 py-2 text-xs font-semibold text-amber-800 dark:text-amber-300">
          Bạn đang xem/sửa dữ liệu của người dùng khác — mọi thay đổi được ghi nhật ký quản trị.
        </div>
        <nav className="flex gap-2 px-5 pt-4 flex-wrap" role="tablist">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`px-4 py-1.5 rounded-full text-xs font-bold ${tab === key ? 'bg-[#a43073] text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'}`}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="flex-1 overflow-y-auto p-5">
          {tab === 'overview' && <AdminUserOverviewTab userId={user.id} />}
          {tab === 'vocab' && <AdminUserVocabTab userId={user.id} notify={notify} />}
          {tab === 'cards' && <AdminUserCardsTab userId={user.id} notify={notify} />}
          {tab === 'settings' && <AdminUserSettingsTab userId={user.id} notify={notify} />}
          {tab === 'library' && <AdminUserLibraryTab userId={user.id} notify={notify} />}
          {tab === 'rewards' && <AdminUserRewardsTab userId={user.id} notify={notify} />}
        </div>
      </aside>
    </div>
  );
};
