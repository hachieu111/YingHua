export type TourId = 'home' | 'reader' | 'upload' | 'library' | 'flashcards' | 'leaderboard' | 'profile' | 'shop' | 'game' | 'sample' | 'admin';

/** Thông tin để chọn nội dung bước: khách hay đã đăng nhập, và điểm neo thực sự được dùng. */
export interface TourStepContext {
  isLoggedIn: boolean;
  target: string | null;
}

export type TourText = string | ((context: TourStepContext) => string);

export interface TourStep {
  id: string;
  /** Giá trị `data-tour`, theo thứ tự ưu tiên. Rỗng: thẻ nằm giữa màn hình, không tô sáng. */
  targets: string[];
  title: TourText;
  body: TourText;
  /** Bước chỉ dành cho một nhóm người xem. */
  audience?: 'guest' | 'user';
  /** Thẻ chào đầu tour; không tính vào tiến độ và bỏ qua khi xem lại. */
  welcome?: boolean;
}

export interface TourDefinition {
  id: TourId;
  steps: TourStep[];
  /** Tour chạy bên trong hộp thoại nên không chờ "không có hộp thoại nào mở". */
  insideModal?: boolean;
  finishLabel: string;
}

export const resolveTourText = (text: TourText, context: TourStepContext): string =>
  typeof text === 'function' ? text(context) : text;
