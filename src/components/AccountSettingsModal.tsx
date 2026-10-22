import React, { useState } from 'react';

interface AccountSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentEmail: string;
  onUpdateEmail: (newEmail: string) => void;
  onLogout: () => void;
  showToast: (msg: string) => void;
}

export const AccountSettingsModal: React.FC<AccountSettingsModalProps> = ({
  isOpen,
  onClose,
  currentEmail,
  onUpdateEmail,
  onLogout,
  showToast
}) => {
  const [activeTab, setActiveTab] = useState<'email' | 'password' | 'logout'>('email');

  // Change Email state
  const [newEmail, setNewEmail] = useState<string>('');
  const [emailPasswordConfirm, setEmailPasswordConfirm] = useState<string>('');

  // Change Password state
  const [oldPassword, setOldPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showPasswords, setShowPasswords] = useState<boolean>(false);

  if (!isOpen) return null;

  // Password strength calculation
  const getPasswordStrength = () => {
    if (!newPassword || newPassword.length === 0) return { label: 'Chưa nhập', level: 0, color: 'text-slate-400' };
    if (newPassword.length < 6) return { label: 'Yếu', level: 1, color: 'text-rose-600' };
    if (newPassword.length < 10) return { label: 'Trung bình', level: 2, color: 'text-amber-600' };
    return { label: 'Rất mạnh', level: 3, color: 'text-[#a43073] font-bold' };
  };

  const strength = getPasswordStrength();

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail || !newEmail.includes('@')) {
      showToast('Vui lòng nhập địa chỉ email hợp lệ!');
      return;
    }
    if (!emailPasswordConfirm) {
      showToast('Vui lòng xác nhận mật khẩu hiện tại!');
      return;
    }
    onUpdateEmail(newEmail);
    showToast(`Đã cập nhật email tài khoản thành công: ${newEmail}`);
    setNewEmail('');
    setEmailPasswordConfirm('');
    onClose();
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!oldPassword) {
      showToast('Vui lòng nhập mật khẩu hiện tại!');
      return;
    }
    if (newPassword.length < 6) {
      showToast('Mật khẩu mới phải có tối thiểu 6 ký tự!');
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast('Xác nhận mật khẩu mới không khớp!');
      return;
    }
    showToast('Đổi mật khẩu thành công! Hãy ghi nhớ mật khẩu mới.');
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-lg rounded-3xl shadow-floating border border-pink-100 overflow-hidden flex flex-col">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 bg-gradient-to-r from-pink-50/70 via-white to-blue-50/40">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073] text-sm font-bold">
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800">Cài đặt tài khoản</h3>
              <p className="text-[11px] text-slate-400 font-medium">
                Quản lý bảo mật, thư điện tử và phiên đăng nhập
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Tab Pills */}
        <div className="flex items-center gap-2 p-3 bg-[#eff4ff] border-b border-blue-100 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('email')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'email'
                ? 'bg-[#f472b6] text-white shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">mail</span>
            <span>Đổi Email</span>
          </button>

          <button
            onClick={() => setActiveTab('password')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'password'
                ? 'bg-[#f472b6] text-white shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">lock_reset</span>
            <span>Đổi Mật Khẩu</span>
          </button>

          <button
            onClick={() => setActiveTab('logout')}
            className={`flex-1 py-2 px-3 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'logout'
                ? 'bg-rose-500 text-white shadow-xs font-bold'
                : 'text-rose-600 hover:bg-rose-50'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">logout</span>
            <span>Đăng Xuất</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="p-6">
          
          {/* TAB 1: CHANGE EMAIL */}
          {activeTab === 'email' && (
            <form onSubmit={handleEmailSubmit} className="flex flex-col gap-4">
              <div className="p-3 rounded-2xl bg-blue-50/70 border border-blue-100 text-xs text-slate-600 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-bold block">
                    Email hiện tại
                  </span>
                  <span className="font-bold text-slate-800 text-sm">{currentEmail}</span>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                  Đã xác thực
                </span>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700">
                  Địa chỉ Email mới
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    alternate_email
                  </span>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="ví dụ: hienvu.new@yinghua.vn"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700">
                  Nhập mật khẩu hiện tại để xác nhận
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    key
                  </span>
                  <input
                    type="password"
                    value={emailPasswordConfirm}
                    onChange={(e) => setEmailPasswordConfirm(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-full text-xs font-semibold text-slate-500 hover:bg-slate-100 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">check</span>
                  <span>Cập nhật Email</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 2: CHANGE PASSWORD */}
          {activeTab === 'password' && (
            <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-3.5">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700">
                  Mật khẩu hiện tại
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    lock
                  </span>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="Mật khẩu đang sử dụng"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-10 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswords(!showPasswords)}
                    className="absolute right-3.5 text-slate-400 hover:text-[#a43073]"
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {showPasswords ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700">
                  Mật khẩu mới
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    lock_open
                  </span>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Tối thiểu 6 ký tự"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>

                {/* Password Strength Meter */}
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

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-700">
                  Xác nhận mật khẩu mới
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    lock_reset
                  </span>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Nhập lại mật khẩu mới"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-full text-xs font-semibold text-slate-500 hover:bg-slate-100 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">save</span>
                  <span>Đổi Mật Khẩu</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: LOGOUT */}
          {activeTab === 'logout' && (
            <div className="flex flex-col items-center text-center gap-4 py-2">
              <div className="w-16 h-16 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center text-2xl shadow-inner">
                <span className="material-symbols-outlined text-[32px]">logout</span>
              </div>

              <div>
                <h4 className="text-base font-bold text-slate-800 font-['Plus_Jakarta_Sans']">
                  Bạn có chắc chắn muốn đăng xuất?
                </h4>
                <p className="text-xs text-slate-500 max-w-sm mt-1 leading-relaxed">
                  Toàn bộ tiến độ đọc truyện, từ vựng tích lũy và chuỗi ngày học của bạn đã được sao lưu an toàn trên hệ thống đám mây.
                </p>
              </div>

              <div className="flex items-center gap-3 w-full pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-2.5 rounded-full text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
                >
                  Ở lại học tiếp
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onLogout();
                    onClose();
                  }}
                  className="flex-1 py-2.5 rounded-full text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 shadow-md transition-all flex items-center justify-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[16px]">logout</span>
                  <span>Đăng xuất ngay</span>
                </button>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
};
