'use client';

import { forwardRef, HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export interface TerminalTextProps extends HTMLAttributes<HTMLSpanElement> {
  /** Text variant */
  variant?: 'default' | 'copper' | 'green' | 'amber' | 'red' | 'muted';
  /** Text size */
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl';
  /** Add glow effect (desktop only) */
  glow?: boolean;
  /** Add cursor blink effect */
  cursor?: boolean;
  /** Force monospace font on mobile too */
  mono?: boolean;
}

/**
 * Terminal-styled text component
 * Desktop: Monospace with optional glow
 * Mobile: System font unless mono prop is set
 */
export const TerminalText = forwardRef<HTMLSpanElement, TerminalTextProps>(
  (
    {
      className,
      variant = 'default',
      size = 'base',
      glow = false,
      cursor = false,
      mono = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={cn(
          // Desktop: Always monospace
          'lg:font-mono',
          // Mobile: System font unless mono is true
          mono && 'font-mono',
          // Size variants
          size === 'xs' && 'text-xs',
          size === 'sm' && 'text-sm',
          size === 'base' && 'text-base',
          size === 'lg' && 'text-lg',
          size === 'xl' && 'text-xl',
          // Color variants
          variant === 'default' && 'text-zinc-300',
          variant === 'copper' && 'text-copper',
          variant === 'green' && 'text-terminal-green',
          variant === 'amber' && 'text-terminal-amber',
          variant === 'red' && 'text-terminal-red',
          variant === 'muted' && 'text-zinc-500',
          // Glow effect (desktop only)
          glow && variant === 'copper' && 'lg:glow-copper',
          glow && variant === 'green' && 'lg:text-glow',
          // Cursor blink
          cursor && 'cursor-blink',
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

TerminalText.displayName = 'TerminalText';

/**
 * Terminal label component
 * Used for key-value displays
 */
export function TerminalLabel({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex items-baseline justify-between gap-2', className)}>
      <TerminalText variant="muted" size="sm">
        {label}
      </TerminalText>
      <TerminalText variant="default" size="sm" mono>
        {children}
      </TerminalText>
    </div>
  );
}
