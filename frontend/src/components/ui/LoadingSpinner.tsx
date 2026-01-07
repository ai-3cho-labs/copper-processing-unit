'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/cn';

const ASCII_SPINNER_FRAMES = ['|', '/', '-', '\\'];
const ASCII_DOTS_FRAMES = ['.  ', '.. ', '...', '   '];

export interface LoadingSpinnerProps {
  /** Spinner size */
  size?: 'sm' | 'md' | 'lg';
  /** Spinner variant */
  variant?: 'spinner' | 'dots' | 'pulse';
  /** Additional class names */
  className?: string;
  /** Loading text */
  text?: string;
}

/**
 * Loading spinner component
 * Uses ASCII animation for terminal aesthetic
 */
export function LoadingSpinner({
  size = 'md',
  variant = 'spinner',
  className,
  text,
}: LoadingSpinnerProps) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const frames =
      variant === 'dots' ? ASCII_DOTS_FRAMES : ASCII_SPINNER_FRAMES;
    const interval = setInterval(() => {
      setFrame((f) => (f + 1) % frames.length);
    }, variant === 'dots' ? 400 : 100);

    return () => clearInterval(interval);
  }, [variant]);

  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-xl',
    lg: 'text-3xl',
  };

  if (variant === 'pulse') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <span
          className={cn(
            'inline-block rounded-full bg-copper animate-pulse',
            size === 'sm' && 'w-2 h-2',
            size === 'md' && 'w-3 h-3',
            size === 'lg' && 'w-4 h-4'
          )}
        />
        {text && <span className="text-zinc-500 text-sm">{text}</span>}
      </div>
    );
  }

  const frames =
    variant === 'dots' ? ASCII_DOTS_FRAMES : ASCII_SPINNER_FRAMES;

  return (
    <div
      className={cn('inline-flex items-center gap-2', className)}
      role="status"
      aria-label={text || 'Loading'}
    >
      <span
        className={cn('font-mono text-copper', sizeClasses[size])}
        aria-hidden="true"
      >
        {frames[frame]}
      </span>
      {text && (
        <span className="text-zinc-500 text-sm font-mono">{text}</span>
      )}
    </div>
  );
}

/**
 * Full-page loading state
 */
export function LoadingPage({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center gap-4">
      <LoadingSpinner size="lg" />
      <p className="text-zinc-500 font-mono text-sm">{text}</p>
    </div>
  );
}

/**
 * Inline loading indicator
 */
export function LoadingInline({ text }: { text?: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-zinc-500">
      <LoadingSpinner size="sm" variant="dots" />
      {text && <span className="text-sm">{text}</span>}
    </span>
  );
}
