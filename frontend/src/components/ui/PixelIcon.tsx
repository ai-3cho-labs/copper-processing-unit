'use client';

import { cn } from '@/lib/cn';

export interface PixelIconProps {
  /** Icon name */
  name: 'pickaxe' | 'ore' | 'cart' | 'gem' | 'coin' | 'lightning' | 'fire' | 'star' | 'chest' | 'clock';
  /** Icon size (in pixels, will be scaled) */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Icon color variant */
  variant?: 'copper' | 'green' | 'gold' | 'red' | 'blue' | 'default';
  /** Additional class names */
  className?: string;
}

/**
 * Pixel art icon component
 * 16x16 base size, rendered as SVG for crisp scaling
 */
export function PixelIcon({
  name,
  size = 'md',
  variant = 'copper',
  className,
}: PixelIconProps) {
  const sizeClass = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
    xl: 'w-8 h-8',
  }[size];

  const colorClass = {
    copper: 'text-copper',
    green: 'text-pixel-green',
    gold: 'text-pixel-gold',
    red: 'text-pixel-red',
    blue: 'text-pixel-blue',
    default: 'text-text-secondary',
  }[variant];

  return (
    <svg
      viewBox="0 0 16 16"
      fill="currentColor"
      className={cn(sizeClass, colorClass, 'pixel-render', className)}
      aria-hidden="true"
    >
      {getIconPath(name)}
    </svg>
  );
}

function getIconPath(name: PixelIconProps['name']) {
  switch (name) {
    case 'pickaxe':
      return (
        <path d="M2 2h2v2H2V2zm2 2h2v2H4V4zm2 2h2v2H6V6zm2 2h2v2H8V8zm2-2h2v2h-2V6zm2-2h2v2h-2V4zm2-2h2v2h-2V2zm-4 8h2v2h-2v-2zm-2 2h2v2H8v-2zm-2 2h2v2H6v-2z" />
      );
    case 'ore':
      return (
        <path d="M4 2h8v2h2v8h-2v2H4v-2H2V4h2V2zm2 4h4v4H6V6z" />
      );
    case 'cart':
      return (
        <path d="M2 6h12v6H2V6zm1 1v4h10V7H3zm1 5h2v2H4v-2zm8 0h2v2h-2v-2z" />
      );
    case 'gem':
      return (
        <path d="M4 2h8v2h2v2l-6 8-6-8V4h2V2zm2 2v2h4V4H6z" />
      );
    case 'coin':
      return (
        <path d="M4 2h8v2h2v8h-2v2H4v-2H2V4h2V2zm2 4v4h4V6H6z" />
      );
    case 'lightning':
      return (
        <path d="M8 0h4v2h-2v2h2v2h-2v2h2v2H8v2H6v2H4v-2h2v-2H4V8h2V6H4V4h2V2h2V0z" />
      );
    case 'fire':
      return (
        <path d="M6 2h4v2h2v2h2v6h-2v2H4v-2H2V6h2V4h2V2zm2 4H6v2H4v2h2v2h4v-2h2v-2h-2V6z" />
      );
    case 'star':
      return (
        <path d="M7 0h2v4h4v2h-3v2h2v2h-2v2h-4v-2H4v-2h2V6H3V4h4V0z" />
      );
    case 'chest':
      return (
        <path d="M2 4h12v2h-1v6H3V6H2V4zm2 3v4h8V7H4zm3 1h2v2H7V8z" />
      );
    case 'clock':
      return (
        <path d="M4 2h8v2h2v8h-2v2H4v-2H2V4h2V2zm3 3v4h3V8H8V5H7z" />
      );
    default:
      return null;
  }
}

/**
 * Animated pixel coin for reward feedback
 */
export function PixelCoin({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const sizeClass = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  }[size];

  return (
    <div
      className={cn(
        sizeClass,
        'rounded-full bg-gradient-to-br from-pixel-gold via-copper to-copper-dim',
        'shadow-[0_0_8px_rgba(251,242,54,0.5)]',
        'animate-float',
        className
      )}
    />
  );
}
