import React from 'react';

interface BrandLogoProps {
  className?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ className = 'w-8 h-8' }) => {
  return (
    <div
      className={`${className} rounded-lg bg-[#4f46e5] flex items-center justify-center shadow-xs shrink-0 select-none overflow-hidden`}
      aria-label="TechMart Support AI Logo"
    >
      <svg viewBox="0 0 36 36" fill="none" className="w-full h-full">
        <rect width="36" height="36" rx="8" fill="url(#tm_grad)" />
        <path
          d="M11 11.5C11 9.84315 12.3431 8.5 14 8.5H23C24.6569 8.5 26 9.84315 26 11.5V19.5C26 21.1569 24.6569 22.5 23 22.5H17.5L13.2 26.2C12.55 26.75 11.5 26.28 11.5 25.4V22.5C11.2 22.1 11 21.3 11 19.5V11.5Z"
          fill="white"
        />
        <circle cx="15" cy="13.2" r="1.15" fill="#3525cd" />
        <path
          d="M19.2 11.8L20.1 14.5L22.8 15.4L20.1 16.3L19.2 19L18.3 16.3L15.6 15.4L18.3 14.5L19.2 11.8Z"
          fill="#3525cd"
        />
        <circle cx="22.8" cy="19.2" r="0.95" fill="#4f46e5" />
        <defs>
          <linearGradient id="tm_grad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
            <stop stopColor="#4f46e5" />
            <stop offset="1" stopColor="#3525cd" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};
