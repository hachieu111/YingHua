import React from 'react';

interface LoginRequiredPageProps {
  onLogin: () => void;
  onRegister: () => void;
  onGoHome: () => void;
}

/** Màn mời đăng nhập khi Khách mở trang dành cho thành viên. */
export const LoginRequiredPage: React.FC<LoginRequiredPageProps> = ({ onLogin, onRegister, onGoHome }) => (
  <div className="w-full max-w-[700px] mx-auto px-4 py-16 flex flex-col items-center text-center gap-6">
    <div className="w-20 h-20 rounded-3xl bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-[#a43073] dark:text-pink-400 shadow-md dark:shadow-none border border-pink-200 dark:border-pink-900/50">
      <span className="material-symbols-outlined text-[42px]">lock</span>
    </div>
    <div className="flex flex-col gap-2">
      <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">
        Yêu cầu đăng nhập tài khoản
      </h2>
      <p className="text-sm text-slate-600 dark:text-slate-300 max-w-lg leading-relaxed">
        Trang này dành riêng cho thành viên của Yinghua để lưu tiến độ học tập, đánh dấu từ vựng và xem lịch sử đọc truyện. Trừ <strong>Trang Chủ</strong> và <strong>Bảng Vàng Danh Dự</strong>, vui lòng đăng nhập để trải nghiệm toàn bộ tính năng!
      </p>
    </div>

    <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
      <button
        onClick={onLogin}
        className="px-6 py-3 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs sm:text-sm shadow-md shadow-pink-300/30 transition-all flex items-center gap-2"
      >
        <span className="material-symbols-outlined text-[18px]">login</span>
        <span>Đăng nhập ngay</span>
      </button>
      <button
        onClick={onRegister}
        className="px-6 py-3 rounded-full bg-white dark:bg-[#1e293b] hover:bg-pink-50 dark:hover:bg-slate-700 text-[#a43073] dark:text-pink-400 border border-pink-200 dark:border-slate-700 font-bold text-xs sm:text-sm shadow-xs dark:shadow-none transition-all flex items-center gap-2"
      >
        <span className="material-symbols-outlined text-[18px]">person_add</span>
        <span>Đăng ký thành viên mới</span>
      </button>
      <button
        onClick={onGoHome}
        className="px-5 py-3 rounded-full text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 text-xs sm:text-sm font-semibold transition-all"
      >
        Về Trang Chủ
      </button>
    </div>
  </div>
);
