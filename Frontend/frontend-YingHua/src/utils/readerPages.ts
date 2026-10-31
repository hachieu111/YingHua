import { ApiPage } from '../api/library';
import { ReaderTarget } from '../types';

/** Bộ trang đang nạp trong trình đọc: một chương (`chapterId`) hoặc bộ ảnh tải nhanh (`chapterId` = null). */
export interface LoadedPages {
  chapterId: number | null;
  pages: ApiPage[];
}

/**
 * Vị trí của đích trong bộ trang đã nạp; null nếu phải nạp lại (đổi chương, ảnh ngoài bộ, hoặc chương chưa chỉ rõ trang
 * để còn áp dụng tiến độ đọc). Nhờ vậy đổi URL trong cùng chương/bộ ảnh chỉ đổi trang, không nạp lại.
 */
export function findLoadedIndex(target: ReaderTarget | null, loaded: LoadedPages | null): number | null {
  if (!target || !loaded || loaded.pages.length === 0 || target.chapterId !== loaded.chapterId) return null;
  const { pages } = loaded;
  let index = -1;
  if (target.pageId !== undefined) index = pages.findIndex(page => page.id === target.pageId);
  else if (target.chapterId !== null && target.pageNo !== undefined) index = pages.findIndex(page => page.page_no === target.pageNo);
  return index >= 0 ? index : null;
}

/** Đích URL của một trang trong bộ đang đọc, để địa chỉ luôn khớp trang đang xem. */
export function targetOfPage(chapterId: number | null, page: ApiPage): ReaderTarget {
  return chapterId === null ? { chapterId: null, pageId: page.id } : { chapterId, pageNo: page.page_no };
}
