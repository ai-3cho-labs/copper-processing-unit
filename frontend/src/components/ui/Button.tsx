'use client';

import { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';
import { LoadingSpinner } from './LoadingSpinner';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  /** Button size */
  size?: 'sm' | 'md' | 'lg';
  /** Show loading state */
  loading?: boolean;
  /** Make button full width */
  fullWidth?: boolean;
  /** Left icon */
  leftIcon?: React.ReactNode;
  /** Right icon */
  rightIcon?: React.ReactNode;
}

/**
 * Button component
 * Pixel-styled with copper accents
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center gap-2',
          'font-medium transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-copper/50 focus:ring-offset-2 focus:ring-offset-bg-dark',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          // Size variants
          size === 'sm' && 'px-3 py-1.5 text-sm rounded-md',
          size === 'md' && 'px-4 py-2 text-sm rounded-lg',
          size === 'lg' && 'px-6 py-3 text-base rounded-lg',
          // Variant styles
          variant === 'primary' && [
            'bg-copper text-white',
            'hover:bg-copper-glow hover:shadow-copper-glow',
            'active:bg-copper-dim',
          ],
          variant === 'secondary' && [
            'bg-bg-card text-text-primary',
            'border border-border',
            'hover:bg-bg-surface hover:border-copper-dim',
          ],
          variant === 'outline' && [
            'bg-transparent text-copper',
            'border border-copper',
            'hover:bg-copper/10',
          ],
          variant === 'ghost' && [
            'bg-transparent text-text-secondary',
            'hover:bg-bg-surface hover:text-text-primary',
          ],
          variant === 'danger' && [
            'bg-pixel-red/20 text-pixel-red',
            'border border-pixel-red/50',
            'hover:bg-pixel-red/30',
          ],
          // Full width
          fullWidth && 'w-full',
          className
        )}
        {...props}
      >
        {/* Loading spinner */}
        {loading && <LoadingSpinner size="sm" />}

        {/* Left icon */}
        {!loading && leftIcon && (
          <span className="flex-shrink-0">{leftIcon}</span>
        )}

        {/* Children */}
        {children}

        {/* Right icon */}
        {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';

/**
 * Icon-only button
 */
export const IconButton = forwardRef<
  HTMLButtonElement,
  Omit<ButtonProps, 'leftIcon' | 'rightIcon' | 'children'> & {
    icon: React.ReactNode;
    'aria-label': string;
  }
>(({ className, icon, size = 'md', ...props }, ref) => {
  return (
    <Button
      ref={ref}
      className={cn(
        // Make it square
        size === 'sm' && 'px-1.5',
        size === 'md' && 'px-2',
        size === 'lg' && 'px-3',
        className
      )}
      size={size}
      {...props}
    >
      {icon}
    </Button>
  );
});

IconButton.displayName = 'IconButton';
