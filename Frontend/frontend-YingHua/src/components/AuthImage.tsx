import React, { useEffect, useState } from 'react';
import { isAbortedError } from '../api/client';
import { fetchFileBlob } from '../api/files';

interface AuthImageProps {
  /** Địa chỉ tệp do máy chủ trả (`/api/v1/files/7`); null = chưa có ảnh. */
  src: string | null | undefined;
  alt: string;
  className?: string;
  /** Hiển thị khi chưa có ảnh hoặc tải lỗi. */
  fallback?: React.ReactNode;
  onLoad?: () => void;
}

/** Ảnh lấy qua API có kèm mã truy cập (ảnh riêng tư), tự thu hồi URL tạm khi không dùng nữa. */
export const AuthImage: React.FC<AuthImageProps> = ({ src, alt, className, fallback, onLoad }) => {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setObjectUrl(null);
    setFailed(false);
    if (!src) return;
    const controller = new AbortController();
    let created: string | null = null;
    fetchFileBlob(src, controller.signal)
      .then(blob => {
        created = URL.createObjectURL(blob);
        setObjectUrl(created);
      })
      .catch(err => {
        if (!isAbortedError(err)) setFailed(true);
      });
    return () => {
      controller.abort();
      if (created) URL.revokeObjectURL(created);
    };
  }, [src]);

  if (objectUrl) return <img src={objectUrl} alt={alt} className={className} onLoad={onLoad} draggable={false} />;

  return (
    <div className={`${className ?? ''} flex items-center justify-center bg-slate-100 dark:bg-slate-700 text-slate-300 dark:text-slate-500`} role="img" aria-label={alt}>
      {failed || !src ? (
        (fallback ?? <span className="material-symbols-outlined text-[28px]">image_not_supported</span>)
      ) : (
        <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin dark:border-pink-900/40"></span>
      )}
    </div>
  );
};
