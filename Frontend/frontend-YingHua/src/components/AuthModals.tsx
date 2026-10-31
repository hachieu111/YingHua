import React, { useState } from 'react';
import { ApiUser, forgotPassword, login, register } from '../api/auth';
import { ApiError } from '../api/client';
import { updateSettings } from '../api/settings';

const MIN_PASSWORD_LENGTH = 8;
// Ba mức tự khai khi đăng ký quy về cấp HSK thấp nhất của nhóm: 1-2 → 1, 3-4 → 3, 5-6 → 5.
const HSK_BY_REGISTER_CHOICE: Record<string, number> = { '1': 1, '2': 3, '3': 5 };

const errorMessage = (err: unknown, fallback: string): string => {
  if (err instanceof ApiError) {
    if (err.code === 'VALIDATION_ERROR') return 'Email không hợp lệ hoặc thông tin chưa đúng định dạng.';
    return err.message;
  }
  return fallback;
};

interface AuthModalsProps {
  mode: 'login' | 'register' | null;
  onClose: () => void;
  onSuccess: (user: ApiUser) => void;
  onSwitchMode: (newMode: 'login' | 'register') => void;
  promptMessage?: string | null;
}

export const AuthModals: React.FC<AuthModalsProps> = ({
  mode,
  onClose,
  onSuccess,
  onSwitchMode,
  promptMessage
}) => {
  // Login form controlled state
  const [loginEmail, setLoginEmail] = useState<string>('');
  const [loginPassword, setLoginPassword] = useState<string>('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginInfo, setLoginInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [loginShowPassword, setLoginShowPassword] = useState<boolean>(false);
  const [rememberMe, setRememberMe] = useState<boolean>(true);

  // Register form controlled state
  const [regName, setRegName] = useState<string>('');
  const [regEmail, setRegEmail] = useState<string>('');
  const [regPassword, setRegPassword] = useState<string>('');
  const [regError, setRegError] = useState<string | null>(null);
  const [regShowPassword, setRegShowPassword] = useState<boolean>(false);
  const [selectedHsk, setSelectedHsk] = useState<string>('2');
  const [learningGoal, setLearningGoal] = useState<'study' | 'entertainment' | 'both'>('both');
  const [agreeTerms, setAgreeTerms] = useState<boolean>(true);

  if (!mode) return null;

  // Password strength calculation for register
  const getPasswordStrength = () => {
    if (!regPassword || regPassword.length === 0) {
      return { label: 'Chưa nhập', level: 0, color: 'text-slate-400 dark:text-slate-500' };
    }
    if (regPassword.length < 6) {
      return { label: 'Yếu', level: 1, color: 'text-rose-600 dark:text-rose-400' };
    }
    if (regPassword.length < 10) {
      return { label: 'Trung bình', level: 2, color: 'text-amber-600 dark:text-amber-400' };
    }
    return { label: 'Rất mạnh', level: 3, color: 'text-[#a43073] dark:text-pink-400 font-bold' };
  };

  const strength = getPasswordStrength();

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail.trim() || !loginPassword) {
      setLoginError('Vui lòng nhập email và mật khẩu.');
      return;
    }
    setSubmitting(true);
    setLoginError(null);
    setLoginInfo(null);
    try {
      onSuccess(await login(loginEmail, loginPassword, rememberMe));
    } catch (err) {
      setLoginError(errorMessage(err, 'Không thể đăng nhập, vui lòng thử lại.'));
    } finally {
      setSubmitting(false);
    }
  };

  // F01.06: gửi liên kết đặt lại mật khẩu. Máy chủ luôn trả thông báo chung, không lộ email có tồn tại hay không.
  const handleForgotPassword = async () => {
    if (!loginEmail.trim()) {
      setLoginError('Nhập email của bạn vào ô phía trên rồi bấm "Quên mật khẩu?".');
      return;
    }
    setSubmitting(true);
    setLoginError(null);
    try {
      setLoginInfo(await forgotPassword(loginEmail));
    } catch (err) {
      setLoginError(errorMessage(err, 'Không thể gửi yêu cầu, vui lòng thử lại.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regEmail.trim()) {
      setRegError('Vui lòng nhập email.');
      return;
    }
    if (regPassword.length < MIN_PASSWORD_LENGTH) {
      setRegError(`Mật khẩu tối thiểu ${MIN_PASSWORD_LENGTH} ký tự.`);
      return;
    }
    if (!agreeTerms) {
      setRegError('Bạn cần đồng ý với Điều khoản dịch vụ để tiếp tục.');
      return;
    }
    setSubmitting(true);
    setRegError(null);
    try {
      const user = await register(regEmail, regPassword, regName);
      try {
        await updateSettings({ learning_goal: learningGoal, hsk_level: HSK_BY_REGISTER_CHOICE[selectedHsk] });
      } catch {
        // Tài khoản đã tạo xong; người dùng chỉnh lại mục tiêu và trình độ trong Cài đặt sau.
      }
      onSuccess(user);
    } catch (err) {
      setRegError(errorMessage(err, 'Không thể tạo tài khoản, vui lòng thử lại.'));
    } finally {
      setSubmitting(false);
    }
  };

  const unsupportedSocialLogin = () => setLoginError('Đăng nhập bằng mạng xã hội chưa được hỗ trợ.');

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="relative w-full max-w-[480px] my-auto">
        
        {/* Glow circles behind card */}
        <div className="absolute -top-10 -left-12 w-48 h-48 bg-pink-300/40 dark:bg-pink-900/20 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-8 -right-10 w-52 h-52 bg-blue-300/40 dark:bg-blue-900/20 rounded-full blur-3xl pointer-events-none"></div>

        {/* Modal Container */}
        <div className="relative bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-xl rounded-3xl p-6 sm:p-8 shadow-floating dark:shadow-none border border-pink-100 dark:border-slate-700 transition-colors duration-300 flex flex-col gap-4">
          
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex items-center justify-center transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>

          {/* Context prompt if redirected from protected page */}
          {promptMessage && (
            <div className="p-3 rounded-2xl bg-pink-50 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-900/40 text-xs font-semibold text-[#a43073] dark:text-pink-400 flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">lock</span>
              <span>{promptMessage}</span>
            </div>
          )}

          {/* ===================== LOGIN VIEW ===================== */}
          {mode === 'login' ? (
            <>
              {/* Daily Streak Top Banner */}
              <div className="flex items-center justify-between gap-2 bg-[#eff4ff] dark:bg-blue-900/20 p-2.5 rounded-2xl border border-blue-100 dark:border-slate-700">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center p-1 shadow-xs shrink-0 dark:bg-slate-800">
                    <img
                      src="/assets/aistudio/image_638c8baa.png"
                      alt="Logo Yinghua"
                      className="w-full h-full object-contain"
                    />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-[#a43073] dark:text-pink-400 uppercase tracking-wider font-bold">
                      Thành tích học tập
                    </span>
                    <span className="text-xs text-slate-800 dark:text-slate-100 font-bold">
                      Chuỗi 7 ngày liên tục 🔥
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-[#0060ac] dark:text-blue-300 font-bold block font-['Noto_Serif_SC']">
                    天天向上
                  </span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 block">Mỗi ngày tiến bộ</span>
                </div>
              </div>

              {/* Title & Subtitle */}
              <div className="flex flex-col gap-1 text-center">
                <h2 className="text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight flex items-center justify-center gap-1.5 font-['Plus_Jakarta_Sans']">
                  <span>Chào mừng trở lại!</span>
                  <span className="text-pink-500">🌸</span>
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Tiếp tục hành trình vừa cày manhua vừa nâng trình tiếng Trung
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleLoginSubmit} className="flex flex-col gap-3.5">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 dark:text-slate-300 font-semibold text-left">
                    Email hoặc Tên đăng nhập
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-[#a43073]/60 text-[18px]">
                      mail
                    </span>
                    <input
                      key="login-email-input"
                      type="text"
                      value={loginEmail}
                      onChange={(e) => {
                        setLoginEmail(e.target.value);
                        setLoginError(null);
                      }}
                      placeholder="ví dụ: sakura@yinghua.vn"
                      autoComplete="username"
                      className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 dark:text-slate-300 font-semibold text-left">
                    Mật khẩu
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-[#a43073]/60 text-[18px]">
                      lock
                    </span>
                    <input
                      key="login-password-input"
                      type={loginShowPassword ? 'text' : 'password'}
                      value={loginPassword}
                      onChange={(e) => {
                        setLoginPassword(e.target.value);
                        setLoginError(null);
                      }}
                      placeholder="••••••••"
                      autoComplete="current-password"
                      className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-10 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setLoginShowPassword(!loginShowPassword)}
                      className="absolute right-3.5 text-slate-400 hover:text-[#a43073] dark:hover:text-pink-400 transition-colors"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {loginShowPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                {loginError && (
                  <p role="alert" className="text-xs font-semibold text-rose-600 dark:text-rose-400">
                    {loginError}
                  </p>
                )}
                {loginInfo && (
                  <p role="status" className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                    {loginInfo}
                  </p>
                )}

                <div className="flex items-center justify-between text-xs pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded accent-[#a43073]"
                    />
                    <span className="text-slate-600 dark:text-slate-300 font-medium">Ghi nhớ đăng nhập</span>
                  </label>
                  <button
                    type="button"
                    onClick={handleForgotPassword}
                    disabled={submitting}
                    className="text-[#a43073] dark:text-pink-400 hover:underline font-bold disabled:opacity-60"
                  >
                    Quên mật khẩu?
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full mt-2 py-2.5 px-6 bg-gradient-to-r from-[#a43073] to-pink-500 text-white rounded-full font-bold text-xs sm:text-sm shadow-md hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-1.5 disabled:opacity-60"
                >
                  <span>{submitting ? 'Đang xử lý...' : 'Đăng nhập ngay'}</span>
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </button>
              </form>

              {/* Social login divider */}
              <div className="relative flex items-center justify-center my-1">
                <div className="w-full h-px bg-slate-200 dark:bg-slate-700"></div>
                <span className="absolute bg-white dark:bg-[#0f172a] px-3 text-[11px] text-slate-400 dark:text-slate-500">
                  Hoặc đăng nhập nhanh bằng
                </span>
              </div>

              {/* Social buttons */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={unsupportedSocialLogin}
                  className="flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl bg-slate-50 dark:bg-[#1e293b] hover:bg-slate-100 dark:hover:bg-slate-700 transition-all border border-slate-100 dark:border-slate-700"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z" fill="#EA4335"></path>
                    <path d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z" fill="#4285F4"></path>
                    <path d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.5s.7 4.8 1.9 7.2l3.7-2.9z" fill="#FBBC05"></path>
                    <path d="M12 24c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 17c1.8 3.7 5.6 7 10.1 7z" fill="#34A853"></path>
                  </svg>
                  <span className="text-[11px] text-slate-600 dark:text-slate-300 font-medium">Google</span>
                </button>

                <button
                  type="button"
                  onClick={unsupportedSocialLogin}
                  className="flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl bg-slate-50 dark:bg-[#1e293b] hover:bg-slate-100 dark:hover:bg-slate-700 transition-all border border-slate-100 dark:border-slate-700"
                >
                  <span className="material-symbols-outlined text-emerald-600 text-[18px] dark:text-emerald-400">chat</span>
                  <span className="text-[11px] text-slate-600 dark:text-slate-300 font-medium">WeChat</span>
                </button>

                <button
                  type="button"
                  onClick={unsupportedSocialLogin}
                  className="flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl bg-slate-50 dark:bg-[#1e293b] hover:bg-slate-100 dark:hover:bg-slate-700 transition-all border border-slate-100 dark:border-slate-700"
                >
                  <span className="material-symbols-outlined text-slate-800 dark:text-slate-200 text-[18px]">brand_awareness</span>
                  <span className="text-[11px] text-slate-600 dark:text-slate-300 font-medium">Apple</span>
                </button>
              </div>

              {/* Switch to Register */}
              <div className="text-center pt-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Chưa có tài khoản Yinghua?{' '}
                  <button
                    onClick={() => onSwitchMode('register')}
                    className="text-[#a43073] dark:text-pink-400 font-bold hover:underline ml-1"
                  >
                    Đăng ký ngay
                  </button>
                </p>
              </div>
            </>
          ) : (
            /* ===================== REGISTER VIEW ===================== */
            <>
              {/* Promo Banner */}
              <div className="flex items-center gap-2 bg-amber-100/70 dark:bg-amber-900/30 text-amber-900 dark:text-amber-400 rounded-full px-4 py-1.5 shadow-xs dark:shadow-none">
                <span className="material-symbols-outlined text-[16px] text-amber-700 dark:text-amber-400">redeem</span>
                <span className="text-xs font-semibold">Nhận ngay 3 ngày mở khóa VIP & Flashcard AI</span>
              </div>

              {/* Title & Subtitle */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-extrabold text-slate-800 dark:text-white font-['Plus_Jakarta_Sans']">
                    Tạo tài khoản Yinghua
                  </h2>
                  <span className="text-pink-500 text-xl">🌸</span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Bắt đầu đọc manhua với bản dịch tương tác & ghi nhớ từ vựng tự nhiên.
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleRegisterSubmit} className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 dark:text-slate-300 font-semibold text-left">
                    Tên hiển thị học tập
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                      person
                    </span>
                    <input
                      key="register-name-input"
                      type="text"
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      placeholder="Lam Hiên Vũ / Tiểu Bạch..."
                      className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 dark:text-slate-300 font-semibold text-left">
                    Địa chỉ Email
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                      mail
                    </span>
                    <input
                      key="register-email-input"
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="duchien.manhua@gmail.com"
                      autoComplete="email"
                      className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 dark:text-slate-300 font-semibold text-left">
                    Mật khẩu
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-slate-400 dark:text-slate-500 text-[18px]">
                      lock
                    </span>
                    <input
                      key="register-password-input"
                      type={regShowPassword ? 'text' : 'password'}
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="Tối thiểu 8 ký tự"
                      autoComplete="new-password"
                      className="w-full bg-[#eff4ff] dark:bg-[#1e293b] text-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 text-xs pl-10 pr-10 py-2.5 rounded-full outline-none focus:bg-white dark:focus:bg-[#1e293b] focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setRegShowPassword(!regShowPassword)}
                      className="absolute right-3.5 text-slate-400 hover:text-[#a43073] dark:hover:text-pink-400"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {regShowPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>

                  {/* Password strength indicator bars */}
                  <div className="flex flex-col gap-1 mt-1">
                    <div className="flex gap-1.5 h-1.5 w-full">
                      <div className={`h-full flex-1 rounded-full transition-colors ${
                        strength.level >= 1 ? (strength.level === 1 ? 'bg-rose-500' : 'bg-amber-400') : 'bg-slate-200 dark:bg-slate-700'
                      }`}></div>
                      <div className={`h-full flex-1 rounded-full transition-colors ${
                        strength.level >= 2 ? (strength.level === 2 ? 'bg-amber-400' : 'bg-[#a43073]') : 'bg-slate-200 dark:bg-slate-700'
                      }`}></div>
                      <div className={`h-full flex-1 rounded-full transition-colors ${
                        strength.level >= 3 ? 'bg-[#a43073]' : 'bg-slate-200 dark:bg-slate-700'
                      }`}></div>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-slate-500 dark:text-slate-400">
                      <span>Độ bảo mật:</span>
                      <span className={strength.color}>{strength.label}</span>
                    </div>
                  </div>
                </div>

                {/* MỤC TIÊU SỬ DỤNG: HỌC TẬP / GIẢI TRÍ / CẢ HAI */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                    <span>Mục tiêu chính của bạn khi dùng Yinghua</span>
                    <span className="text-[10px] text-pink-600 dark:text-pink-400 font-bold bg-pink-50 dark:bg-pink-900/20 px-2 py-0.5 rounded-full">
                      Tuỳ chỉnh lộ trình
                    </span>
                  </label>

                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setLearningGoal('study')}
                      className={`p-2 rounded-2xl flex flex-col items-center text-center transition-all border ${
                        learningGoal === 'study'
                          ? 'bg-[#eff4ff] dark:bg-blue-900/30 border-blue-400 dark:border-blue-500 text-blue-900 dark:text-blue-300 ring-2 ring-blue-100 dark:ring-blue-900/40 shadow-xs dark:shadow-none'
                          : 'bg-slate-50 dark:bg-[#1e293b] border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      <span className="text-lg">📚</span>
                      <span className="text-xs font-bold mt-1">Học tập</span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 leading-tight mt-0.5">Luyện HSK & từ vựng</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setLearningGoal('entertainment')}
                      className={`p-2 rounded-2xl flex flex-col items-center text-center transition-all border ${
                        learningGoal === 'entertainment'
                          ? 'bg-amber-50 dark:bg-amber-900/30 border-amber-400 dark:border-amber-500 text-amber-900 dark:text-amber-400 ring-2 ring-amber-100 dark:ring-amber-900/40 shadow-xs dark:shadow-none'
                          : 'bg-slate-50 dark:bg-[#1e293b] border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      <span className="text-lg">🎮</span>
                      <span className="text-xs font-bold mt-1">Giải trí</span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 leading-tight mt-0.5">Cày manhua thư giãn</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setLearningGoal('both')}
                      className={`p-2 rounded-2xl flex flex-col items-center text-center transition-all border ${
                        learningGoal === 'both'
                          ? 'bg-pink-50 dark:bg-pink-900/20 border-[#a43073] text-[#a43073] dark:text-pink-400 ring-2 ring-pink-100 dark:ring-pink-900/40 shadow-xs dark:shadow-none'
                          : 'bg-slate-50 dark:bg-[#1e293b] border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      <span className="text-lg">✨</span>
                      <span className="text-xs font-bold mt-1">Cả hai</span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 leading-tight mt-0.5">Vừa cày vừa nâng trình</span>
                    </button>
                  </div>
                </div>

                {/* HSK Level Selection Radio Cards */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-700 dark:text-slate-300">Trình độ Tiếng Trung hiện tại</span>
                    <span className="text-[#a43073] dark:text-pink-400 font-normal">Tự điều chỉnh sau</span>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    {[
                      { val: '1', title: 'Mới bắt đầu', desc: 'HSK 1 - 2 • Chưa nhớ nhiều chữ Hán', tag: 'Căn bản', tagColor: 'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-400' },
                      { val: '2', title: 'Sơ - Trung cấp', desc: 'HSK 3 - 4 • Đã nắm cấu trúc câu quen thuộc', tag: 'Phổ biến', tagColor: 'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-300' },
                      { val: '3', title: 'Nâng cao', desc: 'HSK 5 - 6 • Muốn đọc truyện mượt mà & tự nhiên', tag: 'Chuyên sâu', tagColor: 'bg-pink-100 dark:bg-pink-900/30 text-[#a43073] dark:text-pink-400' }
                    ].map((item) => (
                      <label
                        key={item.val}
                        className={`flex items-center gap-3 p-2.5 rounded-2xl cursor-pointer border transition-all ${
                          selectedHsk === item.val
                            ? 'bg-[#eff4ff] dark:bg-blue-900/30 border-blue-300 dark:border-blue-500 ring-2 ring-blue-100 dark:ring-blue-900/40'
                            : 'bg-slate-50 dark:bg-[#1e293b] border-slate-100 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                        }`}
                      >
                        <input
                          type="radio"
                          name="reg_hsk"
                          checked={selectedHsk === item.val}
                          onChange={() => setSelectedHsk(item.val)}
                          className="accent-[#a43073]"
                        />
                        <div className="flex flex-col text-left">
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-100">{item.title}</span>
                          <span className="text-[11px] text-slate-500 dark:text-slate-400">{item.desc}</span>
                        </div>
                        <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full ${item.tagColor}`}>
                          {item.tag}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex items-start gap-2 pt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="mt-0.5 accent-[#a43073]"
                    id="reg_terms"
                  />
                  <label htmlFor="reg_terms" className="cursor-pointer">
                    Tôi đồng ý với <span className="text-[#a43073] dark:text-pink-400 underline">Điều khoản dịch vụ</span> và <span className="text-[#a43073] dark:text-pink-400 underline">Chính sách bảo mật</span> của Yinghua.
                  </label>
                </div>

                {regError && (
                  <p role="alert" className="text-xs font-semibold text-rose-600 dark:text-rose-400">
                    {regError}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full mt-2 py-2.5 px-6 rounded-full bg-gradient-to-r from-pink-500 to-[#a43073] text-white font-bold text-xs sm:text-sm shadow-md hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-1.5 disabled:opacity-60"
                >
                  <span>{submitting ? 'Đang xử lý...' : 'Tạo tài khoản miễn phí'}</span>
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </button>
              </form>

              {/* Switch to Login */}
              <div className="text-center pt-2 border-t border-slate-100 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Đã có tài khoản Yinghua?{' '}
                  <button
                    onClick={() => onSwitchMode('login')}
                    className="text-[#a43073] dark:text-pink-400 font-bold hover:underline ml-1"
                  >
                    Đăng nhập ngay
                  </button>
                </p>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
};
