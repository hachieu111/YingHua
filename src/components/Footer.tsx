import React from 'react';
import { NavigationTab } from '../types';

interface FooterProps {
  setActiveTab: (tab: NavigationTab) => void;
}

export const Footer: React.FC<FooterProps> = ({ setActiveTab }) => {
  return (
    <footer className="w-full bg-white mt-16 border-t border-pink-100/60 shadow-[0_-1px_6px_rgba(0,0,0,0.02)]">
      <div className="max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
        
        <div className="flex items-center gap-3">
          <img
            alt="Yinghua Cherry Blossom Logo"
            className="h-6 w-auto object-contain"
            src="/assets/aistudio/image_638c8baa.png"
          />
          <span className="font-bold text-[#a43073] text-base font-['Plus_Jakarta_Sans']">
            Yinghua 樱花
          </span>
          <span className="text-xs text-slate-500">
            © 2025 Nền tảng học tiếng Trung qua Manhua truyện tranh.
          </span>
        </div>

        <div className="flex items-center gap-6 text-xs font-semibold text-slate-500">
          <button
            onClick={() => setActiveTab('catalog')}
            className="hover:text-[#a43073] transition-colors"
          >
            Trang Chủ
          </button>
          <button
            onClick={() => setActiveTab('leaderboard')}
            className="hover:text-[#a43073] transition-colors"
          >
            Bảng Xếp Hạng
          </button>
          <button
            onClick={() => setActiveTab('reader')}
            className="hover:text-[#a43073] transition-colors"
          >
            Đọc Truyện
          </button>
          <button
            onClick={() => setActiveTab('library')}
            className="hover:text-[#a43073] transition-colors"
          >
            Thư Viện
          </button>
          <button
            onClick={() => setActiveTab('flashcards')}
            className="hover:text-[#a43073] transition-colors"
          >
            Từ Vựng
          </button>
        </div>

      </div>
    </footer>
  );
};
