// Ảnh đại diện có sẵn: mã khớp danh sách của máy chủ (GET /account/avatar-presets), ảnh nằm ở giao diện.
export interface AvatarPresetOption {
  id: string;
  name: string;
  url: string;
}

export const PRESET_AVATARS = [
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

export const DEFAULT_AVATAR_PRESET = 'original';

/** Địa chỉ ảnh của mã ảnh đại diện có sẵn; undefined nếu mã không có trong bộ ảnh. */
export const presetAvatarUrl = (code: string | null | undefined): string | undefined =>
  PRESET_AVATARS.find(preset => preset.id === code)?.url;
