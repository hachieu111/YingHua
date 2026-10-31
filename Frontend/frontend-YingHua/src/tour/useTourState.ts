import { useCallback, useEffect, useRef, useState } from 'react';
import { hasStoredSession } from '../api/auth';
import { getSettings, updateSettings } from '../api/settings';
import { TourId } from './types';

const STORAGE_KEY = 'yinghua-tours';
const KNOWN_TOURS: unknown[] = ['home', 'reader', 'upload', 'library', 'flashcards', 'leaderboard', 'profile', 'shop', 'game', 'sample', 'admin'] satisfies TourId[];

const readLocal = (): string[] => {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '[]');
    // Chỉ giữ mã tour hợp lệ: giá trị lạ gửi lên máy chủ sẽ bị từ chối và chặn việc gộp mãi mãi.
    return Array.isArray(parsed) ? parsed.filter((item): item is TourId => KNOWN_TOURS.includes(item)) : [];
  } catch {
    return [];
  }
};

const writeLocal = (ids: string[]): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Trình duyệt chặn lưu trữ: chỉ mất ghi nhớ giữa các phiên, trong phiên vẫn nhớ ở bộ nhớ.
  }
};

const clearLocal = (): void => {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Không xóa được thì lần sau gộp lại, kết quả vẫn đúng vì phép gộp không nhân bản.
  }
};

const union = (first: string[], second: string[]): string[] => Array.from(new Set([...first, ...second]));

export interface TourState {
  /** Danh sách tour đã xem; null khi chưa biết (đang tải hoặc lỗi mạng), lúc đó không tự mở tour. */
  dismissed: string[] | null;
  markSeen: (id: TourId) => void;
}

/**
 * Đã đăng nhập: danh sách nằm ở máy chủ. Khách: nằm ở localStorage.
 * localStorage còn là hàng chờ: lưu máy chủ thất bại thì giữ lại, lần đăng nhập sau gộp lên rồi xóa.
 */
export const useTourState = (isLoggedIn: boolean): TourState => {
  const [dismissed, setDismissed] = useState<string[] | null>(null);
  const dismissedRef = useRef<string[] | null>(null);

  const apply = useCallback((list: string[] | null) => {
    dismissedRef.current = list;
    setDismissed(list);
  }, []);

  useEffect(() => {
    if (!isLoggedIn) {
      // Còn mã phiên nghĩa là đang khôi phục đăng nhập: chờ, kẻo người dùng cũ bị coi như khách mới.
      apply(hasStoredSession() ? null : readLocal());
      return;
    }
    apply(null);
    const controller = new AbortController();
    getSettings(controller.signal)
      .then(settings => {
        if (controller.signal.aborted) return;
        const stored = settings.dismissed_tours;
        const pending = readLocal();
        if (!Array.isArray(stored)) {
          apply(pending);
          return;
        }
        const merged = union(stored, pending);
        apply(merged);
        if (merged.length === stored.length) {
          clearLocal();
          return;
        }
        updateSettings({ dismissed_tours: merged })
          .then(clearLocal)
          .catch(() => undefined); // Giữ hàng chờ local để gộp ở lần sau.
      })
      .catch(() => undefined); // Không đọc được: để null, trang vẫn dùng bình thường, chỉ không tự mở tour.
    return () => controller.abort();
  }, [isLoggedIn, apply]);

  const markSeen = useCallback(
    (id: TourId) => {
      const current = dismissedRef.current;
      if (current?.includes(id)) return;
      writeLocal(union(readLocal(), [id]));
      // Chưa đọc được danh sách máy chủ thì không ghi đè; hàng chờ local sẽ được gộp sau.
      if (current === null) return;
      const next = [...current, id];
      apply(next);
      if (!isLoggedIn) return;
      updateSettings({ dismissed_tours: next })
        .then(settings => {
          if (Array.isArray(settings.dismissed_tours)) clearLocal();
        })
        .catch(() => undefined); // Giữ hàng chờ local để gộp ở lần sau.
    },
    [apply, isLoggedIn]
  );

  return { dismissed, markSeen };
};
