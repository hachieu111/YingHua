import React, { useState } from 'react';
import { ApiError } from '../api/client';
import { resetPassword } from '../api/auth';

interface ResetPasswordModalProps {
  token: string;
  onClose: () => void;
  onDone: () => void;
}

const MIN_PASSWORD_LENGTH = 8;

/** Bước 2 của quên mật khẩu (F01.06): mở từ liên kết trong email, có dạng /?reset_token=... */
export const ResetPasswordModal: React.FC<ResetPasswordModalProps> = ({ token, onClose, onDone }) => {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Mật khẩu tối thiểu ${MIN_PASSWORD_LENGTH} ký tự`);
      return;
    }
    if (password !== confirm) {
      setError('Xác nhận mật khẩu mới không khớp');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await resetPassword(token, password);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Không thể đặt lại mật khẩu, vui lòng thử lại');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-[440px] bg-white dark:bg-[#0f172a] rounded-3xl p-6 sm:p-8 shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 flex flex-col gap-4">
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng"
          className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex items-center justify-center transition-colors"
        >
          <span className="material-symbols-outlined text-[18px]">close</span>
        </button>

        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">Đặt lại mật khẩu 🌸</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Nhập mật khẩu mới cho tài khoản của bạn. Sau khi đổi, mọi thiết bị đang đăng nhập sẽ bị đăng xuất.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300" htmlFor="reset_new">Mật khẩu mới</label>
            <div className="relative flex items-center">
              <input
                id="reset_new"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(null); }}
                placeholder={`Tối thiểu ${MIN_PASSWORD_LENGTH} ký tự`}
                autoComplete="new-password"
                className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-4 pr-10 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 text-slate-400 hover:text-[#a43073] dark:hover:text-pink-400"
                aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              >
                <span className="material-symbols-outlined text-[18px]">{showPassword ? 'visibility_off' : 'visibility'}</span>
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300" htmlFor="reset_confirm">Xác nhận mật khẩu mới</label>
            <input
              id="reset_confirm"
              type={showPassword ? 'text' : 'password'}
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setError(null); }}
              placeholder="Nhập lại mật khẩu mới"
              autoComplete="new-password"
              className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs px-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
            />
          </div>

          {error && <p role="alert" className="text-xs font-semibold text-rose-600 dark:text-rose-400">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-1 py-2.5 px-6 bg-gradient-to-r from-[#a43073] to-pink-500 text-white rounded-full font-bold text-xs sm:text-sm shadow-md disabled:opacity-60 transition-all"
          >
            {submitting ? 'Đang xử lý...' : 'Đặt lại mật khẩu'}
          </button>
        </form>
      </div>
    </div>
  );
};
