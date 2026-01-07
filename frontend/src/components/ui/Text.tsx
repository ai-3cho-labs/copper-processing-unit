'use client';

import { forwardRef, HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export interface TextProps extends HTMLAttributes<HTMLSpanElement> {
  /** Text variant */
  variant?: 'default' | 'copper' | 'green' | 'gold' | 'red' | 'blue' | 'muted';
  /** Text size */
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl';
  /** Add glow effect */
  glow?: boolean;
  /** Add cursor blink effect */
  cursor?: boolean;
  /** Force monospace font */
  mono?: boolean;
}

/**
 * Text component with pixel art color palette
 */
export const Text = forwardRef<HTMLSpanElement, TextProps>(
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
          // Mono font
          mono && 'font-mono',
          // Size variants
          size === 'xs' && 'text-xs',
          size === 'sm' && 'text-sm',
          size === 'base' && 'text-base',
          size === 'lg' && 'text-lg',
          size === 'xl' && 'text-xl',
          size === '2xl' && 'text-2xl',
          // Color variants (using pixel palette)
          variant === 'default' && 'text-text-primary',
          variant === 'copper' && 'text-copper',
          variant === 'green' && 'text-pixel-green',
          variant === 'gold' && 'text-pixel-gold',
          variant === 'red' && 'text-pixel-red',
          variant === 'blue' && 'text-pixel-blue',
          variant === 'muted' && 'text-text-muted',
          // Glow effect
          glow && variant === 'copper' && 'glow-copper',
          glow && variant === 'green' && 'drop-shadow-[0_0_8px_#6abe30]',
          glow && variant === 'gold' && 'drop-shadow-[0_0_8px_#fbf236]',
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

Text.displayName = 'Text';

/**
 * Label component for key-value displays
 */
export function Label({
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
      <Text variant="muted" size="sm">
        {label}
      </Text>
      <Text variant="default" size="sm" mono>
        {children}
      </Text>
    </div>
  );
}

// Backwards compatibility aliases
export const TerminalText = Text;
export const TerminalLabel = Label;
export type TerminalTextProps = TextProps;
