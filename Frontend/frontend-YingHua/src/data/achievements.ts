import {
  Crown,
  Flower2,
  Moon,
  ScrollText,
  Sprout,
  Star,
  Trophy,
  type LucideIcon
} from 'lucide-react';

export interface AchievementBadge {
  title: string;
  desc: string;
  color: string;
  icon: LucideIcon;
}

export const AVAILABLE_BADGES: AchievementBadge[] = [
  {
    title: 'Thành viên Hoa Anh Đào',
    desc: 'Thành viên thân thiết gắn bó với Yinghua',
    color: 'bg-[#ffd8e7] text-[#85145a] border-pink-300',
    icon: Flower2
  },
  {
    title: 'Đệ Nhất Học Giả',
    desc: 'Top 1 mùa giải điểm EXP cao nhất',
    color: 'bg-amber-100 text-amber-950 border-amber-300',
    icon: Crown
  },
  {
    title: 'Tinh Anh Manhua',
    desc: 'Độc giả đọc hơn 100 trang truyện',
    color: 'bg-blue-100 text-blue-900 border-blue-300',
    icon: Star
  },
  {
    title: 'Người Gieo Hạt',
    desc: 'Tích luỹ hơn 300 từ vựng tiếng Trung',
    color: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    icon: Sprout
  },
  {
    title: 'Vua Từ Vựng HSK 3',
    desc: 'Thành thạo trọn bộ 300 thẻ từ HSK 3',
    color: 'bg-purple-100 text-purple-900 border-purple-300',
    icon: Trophy
  },
  {
    title: 'Cú Đêm Cày Truyện',
    desc: 'Chăm chỉ học và đọc truyện sau 23:00',
    color: 'bg-indigo-100 text-indigo-900 border-indigo-300',
    icon: Moon
  },
  {
    title: 'Dịch Giả Tập Sự',
    desc: 'Tra cứu hơn 150 bong bóng thoại manhua',
    color: 'bg-rose-100 text-rose-900 border-rose-300',
    icon: ScrollText
  }
];
