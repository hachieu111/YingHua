import React, { useState } from 'react';

interface AuthModalsProps {
  mode: 'login' | 'register' | null;
  onClose: () => void;
  onSuccess: () => void;
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
  const [loginEmail, setLoginEmail] = useState<string>('sakura@yinghua.vn');
  const [loginPassword, setLoginPassword] = useState<string>('12345678');
  const [loginShowPassword, setLoginShowPassword] = useState<boolean>(false);
  const [rememberMe, setRememberMe] = useState<boolean>(true);

  // Register form controlled state
  const [regName, setRegName] = useState<string>('Lam Hiên Vũ');
  const [regEmail, setRegEmail] = useState<string>('duchien.manhua@gmail.com');
  const [regPassword, setRegPassword] = useState<string>('');
  const [regShowPassword, setRegShowPassword] = useState<boolean>(false);
  const [selectedHsk, setSelectedHsk] = useState<string>('2');
  const [learningGoal, setLearningGoal] = useState<'study' | 'entertainment' | 'both'>('both');
  const [agreeTerms, setAgreeTerms] = useState<boolean>(true);

  if (!mode) return null;

  // Password strength calculation for register
  const getPasswordStrength = () => {
    if (!regPassword || regPassword.length === 0) {
      return { label: 'Chưa nhập', level: 0, color: 'text-slate-400' };
    }
    if (regPassword.length < 6) {
      return { label: 'Yếu', level: 1, color: 'text-rose-600' };
    }
    if (regPassword.length < 10) {
      return { label: 'Trung bình', level: 2, color: 'text-amber-600' };
    }
    return { label: 'Rất mạnh', level: 3, color: 'text-[#a43073] font-bold' };
  };

  const strength = getPasswordStrength();

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSuccess();
  };

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSuccess();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="relative w-full max-w-[480px] my-auto">
        
        {/* Glow circles behind card */}
        <div className="absolute -top-10 -left-12 w-48 h-48 bg-pink-300/40 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-8 -right-10 w-52 h-52 bg-blue-300/40 rounded-full blur-3xl pointer-events-none"></div>

        {/* Modal Container */}
        <div className="relative bg-white/95 backdrop-blur-xl rounded-3xl p-6 sm:p-8 shadow-floating border border-pink-100 flex flex-col gap-4">
          
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>

          {/* Context prompt if redirected from protected page */}
          {promptMessage && (
            <div className="p-3 rounded-2xl bg-pink-50 border border-pink-200 text-xs font-semibold text-[#a43073] flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">lock</span>
              <span>{promptMessage}</span>
            </div>
          )}

          {/* ===================== LOGIN VIEW ===================== */}
          {mode === 'login' ? (
            <>
              {/* Daily Streak Top Banner */}
              <div className="flex items-center justify-between gap-2 bg-[#eff4ff] p-2.5 rounded-2xl border border-blue-100">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center p-1 shadow-xs shrink-0">
                    <img
                      src="/assets/aistudio/image_638c8baa.png"
                      alt="Logo Yinghua"
                      className="w-full h-full object-contain"
                    />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-[#a43073] uppercase tracking-wider font-bold">
                      Thành tích học tập
                    </span>
                    <span className="text-xs text-slate-800 font-bold">
                      Chuỗi 7 ngày liên tục 🔥
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-[#0060ac] font-bold block font-['Noto_Serif_SC']">
                    天天向上
                  </span>
                  <span className="text-[10px] text-slate-500 block">Mỗi ngày tiến bộ</span>
                </div>
              </div>

              {/* Title & Subtitle */}
              <div className="flex flex-col gap-1 text-center">
                <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center justify-center gap-1.5 font-['Plus_Jakarta_Sans']">
                  <span>Chào mừng trở lại!</span>
                  <span className="text-pink-500">🌸</span>
                </h2>
                <p className="text-xs text-slate-500">
                  Tiếp tục hành trình vừa cày manhua vừa nâng trình tiếng Trung
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleLoginSubmit} className="flex flex-col gap-3.5">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 font-semibold text-left">
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
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="ví dụ: sakura@yinghua.vn"
                      className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 font-semibold text-left">
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
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-10 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setLoginShowPassword(!loginShowPassword)}
                      className="absolute right-3.5 text-slate-400 hover:text-[#a43073] transition-colors"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {loginShowPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded accent-[#a43073]"
                    />
                    <span className="text-slate-600 font-medium">Ghi nhớ đăng nhập</span>
                  </label>
                  <button type="button" className="text-[#a43073] hover:underline font-bold">
                    Quên mật khẩu?
                  </button>
                </div>

                <button
                  type="submit"
                  className="w-full mt-2 py-2.5 px-6 bg-gradient-to-r from-[#a43073] to-pink-500 text-white rounded-full font-bold text-xs sm:text-sm shadow-md hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-1.5"
                >
                  <span>Đăng nhập ngay</span>
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </button>
              </form>

              {/* Social login divider */}
              <div className="relative flex items-center justify-center my-1">
                <div className="w-full h-px bg-slate-200"></div>
                <span className="absolute bg-white px-3 text-[11px] text-slate-400">
                  Hoặc đăng nhập nhanh bằng
                </span>
              </div>

              {/* Social buttons */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={onSuccess}
                  className="flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl bg-slate-50 hover:bg-slate-100 transition-all border border-slate-100"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z" fill="#EA4335"></path>
                    <path d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z" fill="#4285F4"></path>
                    <path d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.5s.7 4.8 1.9 7.2l3.7-2.9z" fill="#FBBC05"></path>
                    <path d="M12 24c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 17c1.8 3.7 5.6 7 10.1 7z" fill="#34A853"></path>
                  </svg>
                  <span className="text-[11px] text-slate-600 font-medium">Google</span>
                </button>

                <button
                  type="button"
                  onClick={onSuccess}
                  className="flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl bg-slate-50 hover:bg-slate-100 transition-all border border-slate-100"
                >
                  <span className="material-symbols-outlined text-emerald-600 text-[18px]">chat</span>
                  <span className="text-[11px] text-slate-600 font-medium">WeChat</span>
                </button>

                <button
                  type="button"
                  onClick={onSuccess}
                  className="flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl bg-slate-50 hover:bg-slate-100 transition-all border border-slate-100"
                >
                  <span className="material-symbols-outlined text-slate-800 text-[18px]">brand_awareness</span>
                  <span className="text-[11px] text-slate-600 font-medium">Apple</span>
                </button>
              </div>

              {/* Switch to Register */}
              <div className="text-center pt-1">
                <p className="text-xs text-slate-500">
                  Chưa có tài khoản Yinghua?{' '}
                  <button
                    onClick={() => onSwitchMode('register')}
                    className="text-[#a43073] font-bold hover:underline ml-1"
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
              <div className="flex items-center gap-2 bg-amber-100/70 text-amber-900 rounded-full px-4 py-1.5 shadow-xs">
                <span className="material-symbols-outlined text-[16px] text-amber-700">redeem</span>
                <span className="text-xs font-semibold">Nhận ngay 3 ngày mở khóa VIP & Flashcard AI</span>
              </div>

              {/* Title & Subtitle */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-extrabold text-slate-800 font-['Plus_Jakarta_Sans']">
                    Tạo tài khoản Yinghua
                  </h2>
                  <span className="text-pink-500 text-xl">🌸</span>
                </div>
                <p className="text-xs text-slate-500">
                  Bắt đầu đọc manhua với bản dịch tương tác & ghi nhớ từ vựng tự nhiên.
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleRegisterSubmit} className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 font-semibold text-left">
                    Tên hiển thị học tập
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                      person
                    </span>
                    <input
                      key="register-name-input"
                      type="text"
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      placeholder="Lam Hiên Vũ / Tiểu Bạch..."
                      className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 font-semibold text-left">
                    Địa chỉ Email
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                      mail
                    </span>
                    <input
                      key="register-email-input"
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="duchien.manhua@gmail.com"
                      className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-600 font-semibold text-left">
                    Mật khẩu
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                      lock
                    </span>
                    <input
                      key="register-password-input"
                      type={regShowPassword ? 'text' : 'password'}
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="Tối thiểu 8 ký tự"
                      className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-10 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setRegShowPassword(!regShowPassword)}
                      className="absolute right-3.5 text-slate-400 hover:text-[#a43073]"
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
                        strength.level >= 1 ? (strength.level === 1 ? 'bg-rose-500' : 'bg-amber-400') : 'bg-slate-200'
                      }`}></div>
                      <div className={`h-full flex-1 rounded-full transition-colors ${
                        strength.level >= 2 ? (strength.level === 2 ? 'bg-amber-400' : 'bg-[#a43073]') : 'bg-slate-200'
                      }`}></div>
                      <div className={`h-full flex-1 rounded-full transition-colors ${
                        strength.level >= 3 ? 'bg-[#a43073]' : 'bg-slate-200'
                      }`}></div>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-slate-500">
                      <span>Độ bảo mật:</span>
                      <span className={strength.color}>{strength.label}</span>
                    </div>
                  </div>
                </div>

                {/* MỤC TIÊU SỬ DỤNG: HỌC TẬP / GIẢI TRÍ / CẢ HAI */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <label className="text-xs font-semibold text-slate-700 flex items-center justify-between">
                    <span>Mục tiêu chính của bạn khi dùng Yinghua</span>
                    <span className="text-[10px] text-pink-600 font-bold bg-pink-50 px-2 py-0.5 rounded-full">
                      Tuỳ chỉnh lộ trình
                    </span>
                  </label>

                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setLearningGoal('study')}
                      className={`p-2 rounded-2xl flex flex-col items-center text-center transition-all border ${
                        learningGoal === 'study'
                          ? 'bg-[#eff4ff] border-blue-400 text-blue-900 ring-2 ring-blue-100 shadow-xs'
                          : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <span className="text-lg">📚</span>
                      <span className="text-xs font-bold mt-1">Học tập</span>
                      <span className="text-[10px] text-slate-400 leading-tight mt-0.5">Luyện HSK & từ vựng</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setLearningGoal('entertainment')}
                      className={`p-2 rounded-2xl flex flex-col items-center text-center transition-all border ${
                        learningGoal === 'entertainment'
                          ? 'bg-amber-50 border-amber-400 text-amber-900 ring-2 ring-amber-100 shadow-xs'
                          : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <span className="text-lg">🎮</span>
                      <span className="text-xs font-bold mt-1">Giải trí</span>
                      <span className="text-[10px] text-slate-400 leading-tight mt-0.5">Cày manhua thư giãn</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setLearningGoal('both')}
                      className={`p-2 rounded-2xl flex flex-col items-center text-center transition-all border ${
                        learningGoal === 'both'
                          ? 'bg-pink-50 border-[#a43073] text-[#a43073] ring-2 ring-pink-100 shadow-xs'
                          : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <span className="text-lg">✨</span>
                      <span className="text-xs font-bold mt-1">Cả hai</span>
                      <span className="text-[10px] text-slate-400 leading-tight mt-0.5">Vừa cày vừa nâng trình</span>
                    </button>
                  </div>
                </div>

                {/* HSK Level Selection Radio Cards */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-700">Trình độ Tiếng Trung hiện tại</span>
                    <span className="text-[#a43073] font-normal">Tự điều chỉnh sau</span>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    {[
                      { val: '1', title: 'Mới bắt đầu', desc: 'HSK 1 - 2 • Chưa nhớ nhiều chữ Hán', tag: 'Căn bản', tagColor: 'bg-amber-100 text-amber-900' },
                      { val: '2', title: 'Sơ - Trung cấp', desc: 'HSK 3 - 4 • Đã nắm cấu trúc câu quen thuộc', tag: 'Phổ biến', tagColor: 'bg-blue-100 text-blue-900' },
                      { val: '3', title: 'Nâng cao', desc: 'HSK 5 - 6 • Muốn đọc truyện mượt mà & tự nhiên', tag: 'Chuyên sâu', tagColor: 'bg-pink-100 text-[#a43073]' }
                    ].map((item) => (
                      <label
                        key={item.val}
                        className={`flex items-center gap-3 p-2.5 rounded-2xl cursor-pointer border transition-all ${
                          selectedHsk === item.val
                            ? 'bg-[#eff4ff] border-blue-300 ring-2 ring-blue-100'
                            : 'bg-slate-50 border-slate-100 hover:bg-slate-100'
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
                          <span className="text-xs font-bold text-slate-800">{item.title}</span>
                          <span className="text-[11px] text-slate-500">{item.desc}</span>
                        </div>
                        <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full ${item.tagColor}`}>
                          {item.tag}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex items-start gap-2 pt-1 text-[11px] text-slate-500">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="mt-0.5 accent-[#a43073]"
                    id="reg_terms"
                  />
                  <label htmlFor="reg_terms" className="cursor-pointer">
                    Tôi đồng ý với <span className="text-[#a43073] underline">Điều khoản dịch vụ</span> và <span className="text-[#a43073] underline">Chính sách bảo mật</span> của Yinghua.
                  </label>
                </div>

                <button
                  type="submit"
                  className="w-full mt-2 py-2.5 px-6 rounded-full bg-gradient-to-r from-pink-500 to-[#a43073] text-white font-bold text-xs sm:text-sm shadow-md hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-1.5"
                >
                  <span>Tạo tài khoản miễn phí</span>
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </button>
              </form>

              {/* Switch to Login */}
              <div className="text-center pt-2 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  Đã có tài khoản Yinghua?{' '}
                  <button
                    onClick={() => onSwitchMode('login')}
                    className="text-[#a43073] font-bold hover:underline ml-1"
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
