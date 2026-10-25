import React from 'react';
import { AuthImage } from './AuthImage';

interface ProfileAvatarProps {
  /** Avatar đã tải lên máy chủ (`/api/v1/files/7`); null = dùng ảnh gợi ý. */
  serverUrl?: string | null;
  /** Ảnh gợi ý hiển thị khi chưa có avatar tải lên hoặc tải lỗi. */
  fallbackSrc: string;
  alt: string;
  className?: string;
}

/** Avatar người dùng: ưu tiên ảnh tải lên (riêng tư, tải kèm mã truy cập), không có thì dùng ảnh gợi ý. */
export const ProfileAvatar: React.FC<ProfileAvatarProps> = ({ serverUrl, fallbackSrc, alt, className }) => {
  if (!serverUrl) return <img src={fallbackSrc} alt={alt} className={className} />;
  return (
    <AuthImage
      src={serverUrl}
      alt={alt}
      className={className}
      fallback={<img src={fallbackSrc} alt={alt} className="w-full h-full rounded-full object-cover" />}
    />
  );
};
