import React, { useState } from 'react';
import { UserProfileData } from '../types';
import { AVAILABLE_BADGES } from '../data/achievements';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  userProfile: UserProfileData;
  onSaveProfile: (updated: Partial<UserProfileData>) => void;
  showToast: (msg: string) => void;
}

const PRESET_AVATARS = [
  {
    id: 'original',
    name: 'Lam Hiên Vũ',
    url: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDouZjBIU9lI8mNPf-eu9v9WtamqAGj2p9GPjLNQt-W3hkLMoboWClFeN1wnO4reJTt623UqgtV7sJWTBZNtrFULAAXa_41CVt1ROrHqL64Mt0hCpqhgY5UTLxSAkXf-fdF7PnB-_CsuutWeSJYspalRkRCCKxE8AkIKcYGrOLBFHbjBFp6Ljll9-mSx90EzZUcRzR8Cj7_VM-vjsotklPmMQYldFasjlGLovnzMABNqni9r2ipQklp'
  },
  {
    id: 'sakura_flower',
    name: 'Hoa Anh Đào Yinghua',
    url: '/assets/aistudio/image_638c8baa.png'
  },
  {
    id: 'bach_thien',
    name: 'Bạch Thiển (Quán quân)',
    url: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDjUr4FMb4MgwcGmdyBYosbOItcdlvEkxu9VuOkv4yChU6EPBmWHSxMyaIG2w7JyQSlJ3zh4VkfCAHFuSSY-0bwHegxn1MY8EwBXQDq5YEuIMo6kduC811ATR-vUrWSRZiJDDw4Dv4kfEcji9H1h-Frrh68cI9XZpGjabLqD7QeFSRUy5m8nMQbUcYmyVvydukRzllNvxE0yWo2vXMWSiwKMCQRmHm73bSNJPX1IKlAOx5ut-6odYJ9'
  },
  {
    id: 'tieu_vu_tru',
    name: 'Tiểu Vũ Trụ',
    url: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA_uMPLrijjganO12yjzcqBT4iRom9EHHW5tkEKYy0s6bzONjjZJOsKMo1tHWZ8Mi_cej435rLx8tBS0eHe8LCMLexJUN5tPcGo1NTdFzzBTxXd91zyr0yJy6Da72aTL-lo0Szz_EN_4TtVoml8l2HoF628gmirX8rQ_7mEIpNRWkRQZ9pB6UXBT70FsGbmfLvFNCAM-h3ZCTUHpDJNDHRqG45SO6jydevpkFNc0CxToqjFs2LON3aY'
  },
  {
    id: 'mac_van',
    name: 'Mạc Vấn',
    url: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBVjkBiWmwVafJMFy9b38FOH42tFaihJElRLi9nDAV5kkc2iezdzuP8nQD_WcpKsTydMuQn7_BGS5NPclc7mAdJJyAjVL3PVN0CQfH4wExm8ENDZuz7UW0VNFXP-dC-NzRpy-7pc9aq-C3NNor8-m5kSohpalM-Ea01ca-lKrmXCfBGC1iQjCcKw3fvo3hfAom1pRQq31RocIYeNSPlzBzO6CsCRH05YkdOae0ppcgrnQlYGso1XlIQ'
  },
  {
    id: 'lac_ly',
    name: 'Lạc Ly',
    url: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA9DFVyAwp3qs6bCCAS8H7_nzT-vbOYDPJDn1sNqw2e5llwn6Uto6fdyGaQKtiWpeJBD07ciJ_TsXHxC_7piD5Mb4fO5S3MIAIWQPQsagQhycr6kl0mfSytJWJ3I1ik8Bu9TPR-bvLR4y9YezoQpbtLX9ir-kDT0dKus1c04xqvISFIQWbYsZ-l5T0KOSCsSCNoPqxw5lOdQofxtc9g1tSnZlOZgE_5h1ddlLI2IfB1P52BGomg0e5T'
  }
];

export const EditProfileModal: React.FC<EditProfileModalProps> = ({
  isOpen,
  onClose,
  userProfile,
  onSaveProfile,
  showToast
}) => {
  const [name, setName] = useState<string>(userProfile?.name || '');
  const [chineseName, setChineseName] = useState<string>(userProfile?.chineseName || '');
  const [selectedAvatar, setSelectedAvatar] = useState<string>(userProfile?.avatar || '');
  const [selectedBadge, setSelectedBadge] = useState<string>(userProfile?.badge || '');

  if (!isOpen) return null;

  const handleCustomAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          setSelectedAvatar(event.target.result as string);
          showToast('Đã tải ảnh đại diện mới thành công!');
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      showToast('Tên hiển thị không được để trống!');
      return;
    }
    onSaveProfile({
      name: name.trim(),
      chineseName: chineseName.trim() || '轩宇',
      avatar: selectedAvatar,
      badge: selectedBadge
    });
    showToast('Cập nhật hồ sơ cá nhân thành công!');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white w-full max-w-xl rounded-3xl shadow-floating border border-pink-100 overflow-hidden flex flex-col my-auto max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-pink-100 bg-gradient-to-r from-pink-50/70 via-white to-pink-50/40 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-pink-100 flex items-center justify-center text-[#a43073] text-sm font-bold">
              <span className="material-symbols-outlined text-[20px]">edit_note</span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800">Chỉnh sửa hồ sơ</h3>
              <p className="text-[11px] text-slate-400 font-medium">
                Cập nhật tên, ảnh đại diện và thẻ danh hiệu đang hiển thị
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

        {/* Scrollable Form Body */}
        <form onSubmit={handleSave} className="p-6 overflow-y-auto custom-scrollbar flex flex-col gap-6">
          
          {/* SECTION 1: AVATAR SELECTION */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#a43073]">account_circle</span>
              <span>1. Ảnh đại diện (Avatar)</span>
            </span>

            {/* Current Selected Avatar Preview & Upload */}
            <div className="flex items-center gap-4 p-3.5 rounded-2xl bg-[#eff4ff] border border-blue-100">
              <div className="relative shrink-0">
                <img
                  src={selectedAvatar}
                  alt="Avatar Preview"
                  className="w-16 h-16 rounded-full object-cover ring-4 ring-pink-300 shadow-md bg-white"
                />
                <span className="absolute -bottom-1 -right-1 w-5 h-5 bg-[#a43073] text-white rounded-full flex items-center justify-center text-[10px]">
                  ✓
                </span>
              </div>

              <div className="flex flex-col gap-1 flex-1">
                <span className="text-xs font-bold text-slate-800">Ảnh đang chọn</span>
                <span className="text-[11px] text-slate-500">
                  Chọn một nhân vật bên dưới hoặc tải ảnh avatar từ thiết bị của bạn
                </span>
                
                {/* File input button */}
                <label className="mt-1 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white hover:bg-pink-50 text-[#a43073] border border-pink-200 text-xs font-semibold cursor-pointer w-fit shadow-xs transition-colors">
                  <span className="material-symbols-outlined text-[16px]">upload</span>
                  <span>Tải ảnh từ máy tính</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleCustomAvatarUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Avatar Preset Grid */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[11px] font-semibold text-slate-500">
                Gợi ý avatar manhua & biểu trưng:
              </span>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2.5">
                {PRESET_AVATARS.map((av) => {
                  const isSelected = selectedAvatar === av.url;
                  return (
                    <button
                      type="button"
                      key={av.id}
                      onClick={() => setSelectedAvatar(av.url)}
                      className={`relative rounded-2xl p-1 flex flex-col items-center gap-1 transition-all ${
                        isSelected
                          ? 'ring-2 ring-[#a43073] bg-pink-50 scale-105'
                          : 'hover:bg-slate-50 border border-slate-100'
                      }`}
                    >
                      <img
                        src={av.url}
                        alt={av.name}
                        className="w-12 h-12 rounded-full object-cover shadow-xs bg-white"
                      />
                      <span className="text-[10px] text-slate-700 font-medium truncate max-w-[70px]">
                        {av.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* SECTION 2: NAME EDITING */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#0060ac]">badge</span>
              <span>2. Tên hiển thị & Chữ Hán</span>
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">
                  Tên hiển thị học tập
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    person
                  </span>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Lam Hiên Vũ"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">
                  Tên chữ Hán (nếu có)
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3.5 text-slate-400 text-[18px]">
                    translate
                  </span>
                  <input
                    type="text"
                    value={chineseName}
                    onChange={(e) => setChineseName(e.target.value)}
                    placeholder="轩宇"
                    className="w-full bg-[#eff4ff] text-slate-800 text-xs pl-10 pr-4 py-2.5 rounded-full outline-none focus:bg-white focus:ring-2 focus:ring-[#f472b6] transition-all font-['Noto_Serif_SC'] font-semibold"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 3: ACHIEVEMENT BADGE SELECTION */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] text-amber-600">military_tech</span>
                <span>3. Thẻ thành tựu / Danh hiệu trang bị</span>
              </span>
              <span className="text-[11px] text-[#a43073] font-bold">
                Đang dùng: {selectedBadge}
              </span>
            </div>

            <p className="text-[11px] text-slate-500">
              Chọn danh hiệu muốn hiển thị nổi bật bên cạnh tên tài khoản của bạn:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {AVAILABLE_BADGES.map((b) => {
                const isSelected = selectedBadge.includes(b.title);
                const BadgeIcon = b.icon;
                return (
                  <div
                    key={b.title}
                    onClick={() => setSelectedBadge(b.title)}
                    className={`p-3 rounded-2xl cursor-pointer border transition-all flex items-start gap-3 ${
                      isSelected
                        ? 'bg-pink-50/80 border-[#a43073] ring-2 ring-pink-200'
                        : 'bg-slate-50/70 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <span className={`w-10 h-10 rounded-xl border shrink-0 flex items-center justify-center ${b.color}`}>
                      <BadgeIcon className="w-5 h-5" strokeWidth={2.2} aria-hidden="true" />
                    </span>
                    <div className="flex flex-col min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-800 truncate">
                          {b.title}
                        </span>
                        {isSelected && (
                          <span className="w-4 h-4 rounded-full bg-[#a43073] text-white flex items-center justify-center text-[10px]">
                            ✓
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">
                        {b.desc}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-3 shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-full bg-gradient-to-r from-pink-500 to-[#a43073] text-white font-bold text-xs shadow-md hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">save</span>
              <span>Lưu thay đổi hồ sơ</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
