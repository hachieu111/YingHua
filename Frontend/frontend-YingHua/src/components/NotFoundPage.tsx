import React from 'react';

interface NotFoundPageProps {
  onGoHome: () => void;
}

export const NotFoundPage: React.FC<NotFoundPageProps> = ({ onGoHome }) => (
  <div className="w-full max-w-[700px] mx-auto px-4 py-16 flex flex-col items-center text-center gap-6">
    <div className="w-20 h-20 rounded-3xl bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-[#a43073] dark:text-pink-400 shadow-md dark:shadow-none border border-pink-200 dark:border-pink-900/50">
      <span className="material-symbols-outlined text-[42px]">explore_off</span>
    </div>
    <div className="flex flex-col gap-2">
      <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">Không tìm thấy trang</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300 max-w-lg leading-relaxed">
        Đường dẫn bạn mở không tồn tại hoặc đã bị thay đổi. Hãy quay về Trang Chủ để tiếp tục khám phá truyện tranh.
      </p>
    </div>
    <button
      onClick={onGoHome}
      className="px-6 py-3 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm shadow-md shadow-pink-300/30 transition-all flex items-center gap-2"
    >
      <span className="material-symbols-outlined text-[18px]">home</span>
      <span>Về Trang Chủ</span>
    </button>
  </div>
);
