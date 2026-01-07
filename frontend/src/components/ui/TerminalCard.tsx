'use client';

import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface TerminalCardProps extends HTMLAttributes<HTMLDivElement> {
  /** Card title (displayed in header) */
  title?: string;
  /** Card variant */
  variant?: 'default' | 'highlight' | 'success' | 'error';
  /** Remove default padding */
  noPadding?: boolean;
  /** Header right content */
  headerRight?: ReactNode;
}

/**
 * Terminal-styled card component
 * Desktop: Retro terminal aesthetic with borders
 * Mobile: Clean modern card design
 */
export const TerminalCard = forwardRef<HTMLDivElement, TerminalCardProps>(
  (
    {
      className,
      title,
      variant = 'default',
      noPadding = false,
      headerRight,
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
          // Desktop: Terminal aesthetic
          'lg:rounded-sm lg:border',
          'lg:bg-terminal-card lg:border-terminal-border',
          // Mobile: Clean card design
          'bg-zinc-900/90 border border-zinc-800',
          // Variant styles (desktop)
          variant === 'highlight' &&
            'lg:border-copper lg:shadow-copper-glow',
          variant === 'success' && 'lg:border-terminal-green',
          variant === 'error' && 'lg:border-terminal-red',
          className
        )}
        {...props}
      >
        {/* Header */}
        {title && (
          <div
            className={cn(
              'px-4 py-2.5 border-b flex items-center justify-between',
              // Desktop: Terminal style header
              'lg:border-terminal-border lg:bg-terminal-bg/50',
              // Mobile: Clean header
              'border-zinc-800 bg-zinc-900/50'
            )}
          >
            <span
              className={cn(
                'font-medium text-sm',
                // Desktop: Copper text with prompt
                'lg:font-mono lg:text-copper',
                // Mobile: White text
                'text-zinc-200'
              )}
            >
              <span className="hidden lg:inline text-copper-dim">&gt; </span>
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

TerminalCard.displayName = 'TerminalCard';
