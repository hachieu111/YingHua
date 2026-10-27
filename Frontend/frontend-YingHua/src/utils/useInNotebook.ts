import { useCallback, useEffect, useState } from 'react';
import { getSavedStatus } from '../api/vocab';

/**
 * Từ `term` đã có trong Sổ tay chưa — hỏi máy chủ khi từ đổi và mỗi khi quay lại tab, nên đúng cả sau khi tải lại
 * trang hay khi từ vừa bị xóa ở Sổ tay. Trả kèm hàm đánh dấu "đã lưu" ngay sau khi lưu thành công.
 */
export function useInNotebook(term: string | null, isLoggedIn: boolean): [boolean, () => void] {
  const [inNotebook, setInNotebook] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === 'visible') setTick(value => value + 1);
    };
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, []);

  useEffect(() => {
    setInNotebook(false);
    if (!term || !isLoggedIn) return;
    const controller = new AbortController();
    getSavedStatus({ terms: [term], bubbleIds: [], pageId: null }, controller.signal)
      .then(status => setInNotebook(status.terms.includes(term)))
      .catch(() => {
        // Không hỏi được máy chủ: để nút lưu bấm được như bình thường, máy chủ vẫn chống trùng (F07.02).
      });
    return () => controller.abort();
  }, [term, isLoggedIn, tick]);

  const markSaved = useCallback(() => setInNotebook(true), []);
  return [inNotebook, markSaved];
}
