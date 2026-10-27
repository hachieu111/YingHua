import { useEffect } from 'react';

const APP_NAME = 'YingHua';

/** Đặt tiêu đề tab trình duyệt theo trang đang xem; để trống thì dùng tiêu đề mặc định của index.html. */
export function useDocumentTitle(pageTitle: string | null): void {
  useEffect(() => {
    if (!pageTitle) return;
    const previous = document.title;
    document.title = `${pageTitle} · ${APP_NAME}`;
    return () => {
      document.title = previous;
    };
  }, [pageTitle]);
}
