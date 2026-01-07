'use client';

import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Card title (displayed in header) */
  title?: string;
  /** Card variant */
  variant?: 'default' | 'highlight' | 'success' | 'error';
  /** Remove default padding */
  noPadding?: boolean;
  /** Header right content */
  headerRight?: ReactNode;
  /** Add pixel accent border */
  pixelAccent?: boolean;
}

/**
 * Card component with pixel art aesthetic
 * Warm brown backgrounds with rounded corners
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      title,
      variant = 'default',
      noPadding = false,
      headerRight,
      pixelAccent = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          // Base styles
          'rounded-lg overflow-hidden',
          'bg-bg-card border border-border',
          // Shadow
          'shadow-lg',
          // Variant styles
          variant === 'highlight' && 'border-copper shadow-copper-glow',
          variant === 'success' && 'border-pixel-green',
          variant === 'error' && 'border-pixel-red',
          // Pixel accent
          pixelAccent && 'border-2 border-copper-dim',
          className
        )}
        {...props}
      >
        {/* Header */}
        {title && (
          <div
            className={cn(
              'px-4 py-3 border-b border-border flex items-center justify-between',
              'bg-bg-dark/50'
            )}
          >
            <span
              className={cn(
                'font-medium text-sm text-copper',
                variant === 'highlight' && 'text-copper-glow'
              )}
            >
              {title}
            </span>
            {headerRight && (
              <div className="flex items-center gap-2">{headerRight}</div>
            )}
          </div>
        )}

        {/* Content */}
        <div className={cn(!noPadding && 'p-4')}>{children}</div>
      </div>
    );
  }
);

Card.displayName = 'Card';

// Backwards compatibility alias
export const TerminalCard = Card;
export type TerminalCardProps = CardProps;
