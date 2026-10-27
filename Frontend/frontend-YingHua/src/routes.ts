import { NavigationTab, ReaderTarget } from './types';

/** Đường dẫn của từng mục điều hướng chính. */
export const TAB_PATHS: Record<NavigationTab, string> = {
  catalog: '/',
  reader: '/doc',
  library: '/thu-vien',
  flashcards: '/tu-vung',
  leaderboard: '/xep-hang',
  profile: '/ho-so',
  admin: '/quan-tri'
};

/** Trang mẫu để thử Hover & Dịch (F04.16); không thuộc thanh điều hướng chính. */
export const SAMPLE_PAGE_PATH = '/trang-mau';

/** Tham số `?muc=` của trang từ vựng: cuộn tới khu kiểm tra. */
export const QUIZ_SECTION_PARAM = 'muc';
export const QUIZ_SECTION_VALUE = 'kiem-tra';

/** Mục điều hướng ứng với đường dẫn hiện tại; null khi không thuộc mục nào (vd. trang 404). */
export const tabFromPathname = (pathname: string): NavigationTab | null => {
  if (pathname === '/') return 'catalog';
  if (pathname === '/doc' || pathname.startsWith('/doc/')) return 'reader';
  const entry = (Object.entries(TAB_PATHS) as [NavigationTab, string][]).find(([, path]) => path === pathname);
  return entry ? entry[0] : null;
};

/** Đường dẫn trình đọc cho một chương/trang (mọi số đều là số nguyên do máy chủ cấp). */
export const readerPath = (target: ReaderTarget | null): string => {
  if (!target) return TAB_PATHS.reader;
  if (target.chapterId === null) {
    return target.pageId !== undefined ? `${TAB_PATHS.reader}/anh/${target.pageId}` : TAB_PATHS.reader;
  }
  const query = new URLSearchParams();
  if (target.pageNo !== undefined) query.set('trang', String(target.pageNo));
  if (target.pageId !== undefined) query.set('anh', String(target.pageId));
  const suffix = query.toString();
  return `${TAB_PATHS.reader}/${target.chapterId}${suffix ? `?${suffix}` : ''}`;
};

/** Ép chuỗi trên URL về số nguyên dương; không hợp lệ thì trả null. */
export const parsePositiveInt = (value: string | null | undefined): number | null => {
  if (value === null || value === undefined || !/^[1-9]\d{0,9}$/.test(value)) return null;
  return Number(value);
};
