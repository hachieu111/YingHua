import React, { useEffect, useMemo } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router';
import { ReaderTarget } from '../types';
import { parsePositiveInt } from '../routes';
import { ComicReader } from './ComicReader';
import { LoginRequiredPage } from './LoginRequiredPage';
import { NotFoundPage } from './NotFoundPage';

type ComicReaderProps = React.ComponentProps<typeof ComicReader>;

interface ReaderRouteProps extends Omit<ComicReaderProps, 'target'> {
  onLogin: () => void;
  onRegister: () => void;
  onGoHome: () => void;
  /** Báo đường dẫn trình đọc hợp lệ đang mở để mục "Đọc truyện" quay lại đúng chương. */
  onPathChange: (path: string) => void;
}

/** Trình đọc theo URL: /doc, /doc/:chapterId?trang=N&anh=ID, /doc/anh/:pageId. Tham số sai về trang 404. */
export const ReaderRoute: React.FC<ReaderRouteProps> = ({ onLogin, onRegister, onGoHome, onPathChange, ...readerProps }) => {
  const { chapterId, pageId } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();

  const hasChapterParam = chapterId !== undefined;
  const hasPageParam = pageId !== undefined;
  const chapterNumber = parsePositiveInt(chapterId);
  const pageIdNumber = parsePositiveInt(pageId);
  const pageNoParam = searchParams.get('trang');
  const pageNo = parsePositiveInt(pageNoParam);
  const queryPageIdParam = searchParams.get('anh');
  const queryPageId = parsePositiveInt(queryPageIdParam);

  const invalid =
    (hasChapterParam && chapterNumber === null) ||
    (hasPageParam && pageIdNumber === null) ||
    (pageNoParam !== null && pageNo === null) ||
    (queryPageIdParam !== null && queryPageId === null);

  // Giữ nguyên danh tính `target` giữa các lần render để trình đọc không nạp lại chương vô cớ.
  const target = useMemo<ReaderTarget | null>(() => {
    if (invalid) return null;
    if (chapterNumber !== null) {
      return { chapterId: chapterNumber, pageNo: pageNo ?? undefined, pageId: queryPageId ?? undefined };
    }
    if (pageIdNumber !== null) return { chapterId: null, pageId: pageIdNumber };
    return null;
  }, [invalid, chapterNumber, pageNo, queryPageId, pageIdNumber]);

  const currentPath = location.pathname + location.search;
  useEffect(() => {
    if (target) onPathChange(currentPath);
  }, [target, currentPath, onPathChange]);

  if (invalid) return <NotFoundPage onGoHome={onGoHome} />;
  // Khách chỉ mở được khi đã có chương cụ thể (đọc thử); chưa chọn truyện thì mời đăng nhập.
  if (!readerProps.isLoggedIn && target === null) {
    return <LoginRequiredPage onLogin={onLogin} onRegister={onRegister} onGoHome={onGoHome} />;
  }
  return <ComicReader {...readerProps} target={target} />;
};
