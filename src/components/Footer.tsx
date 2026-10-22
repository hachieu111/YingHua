import React from 'react';
import { NavigationTab } from '../types';

interface FooterProps {
  setActiveTab: (tab: NavigationTab) => void;
}

export const Footer: React.FC<FooterProps> = ({ setActiveTab }) => {
  return (
    <footer className="w-full bg-white mt-16 border-t border-pink-100/60 shadow-[0_-1px_6px_rgba(0,0,0,0.02)]">
      <div className="max-w-[1440px] mx-auto px-4 md:px-8 lg:px-12 py-8 flex flex-col md:flex-row items-center justify-between gap-5">
        
        <div className="flex flex-col sm:flex-row items-center gap-x-3 gap-y-2">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-full overflow-hidden shadow-sm border border-pink-200/80 bg-white flex items-center justify-center shrink-0">
              <img
                alt="Yinghua Cherry Blossom Logo"
                className="w-full h-full object-contain rounded-full p-0.5"
                src="/assets/imagetest/media_1792630135660_75497c66.png"
              />
            </span>
            <span className="font-bold text-lg text-[#a43073] tracking-tight font-['Plus_Jakarta_Sans']">
              Yinghua <span className="text-xs text-[#64a8fe] font-medium font-['Noto_Serif_SC']">(樱花)</span>
            </span>
          </div>
          <span className="text-xs text-slate-500 text-center sm:text-left">
            © 2026 Nền tảng học tiếng Trung qua Manhua truyện tranh
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
