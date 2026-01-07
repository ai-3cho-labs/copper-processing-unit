'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/cn';
import { PixelIcon } from './PixelIcon';

export interface PixelToastProps {
  /** Toast message */
  message: string;
  /** Toast variant */
  variant?: 'success' | 'error' | 'info';
  /** Show the toast */
  show: boolean;
  /** Duration in ms (0 for persistent) */
  duration?: number;
  /** Callback when toast closes */
  onClose?: () => void;
}

/**
 * Pixel-styled toast notification
 * Used for mobile transaction feedback
 */
export function PixelToast({
  message,
  variant = 'success',
  show,
  duration = 3000,
  onClose,
}: PixelToastProps) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    if (show) {
      setVisible(true);
      setExiting(false);

      if (duration > 0) {
        const timer = setTimeout(() => {
          setExiting(true);
          setTimeout(() => {
            setVisible(false);
            onClose?.();
          }, 200);
        }, duration);

        return () => clearTimeout(timer);
      }
      return;
    } else {
      setExiting(true);
      setTimeout(() => setVisible(false), 200);
      return;
    }
  }, [show, duration, onClose]);

  if (!visible) return null;

  const variantStyles = {
    success: {
      bg: 'bg-pixel-green/20',
      border: 'border-pixel-green/50',
      text: 'text-pixel-green',
      icon: 'star' as const,
    },
    error: {
      bg: 'bg-pixel-red/20',
      border: 'border-pixel-red/50',
      text: 'text-pixel-red',
      icon: 'fire' as const,
    },
    info: {
      bg: 'bg-pixel-blue/20',
      border: 'border-pixel-blue/50',
      text: 'text-pixel-blue',
      icon: 'gem' as const,
    },
  };

  const style = variantStyles[variant];

  return (
    <div
      className={cn(
        'fixed bottom-20 left-1/2 -translate-x-1/2 z-50',
        'px-4 py-3 rounded-lg border',
        'flex items-center gap-3',
        'shadow-lg backdrop-blur-sm',
        'transition-all duration-200',
        style.bg,
        style.border,
        exiting ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'
      )}
      role="alert"
    >
      <PixelIcon
        name={style.icon}
        size="md"
        variant={variant === 'success' ? 'green' : variant === 'error' ? 'red' : 'blue'}
      />
      <span className={cn('text-sm font-medium', style.text)}>
        {message}
      </span>
    </div>
  );
}

/**
 * Hook to manage toast state
 */
export function usePixelToast() {
  const [toastState, setToastState] = useState<{
    show: boolean;
    message: string;
    variant: 'success' | 'error' | 'info';
  }>({
    show: false,
    message: '',
    variant: 'success',
  });

  const showToast = (
    message: string,
    variant: 'success' | 'error' | 'info' = 'success'
  ) => {
    setToastState({ show: true, message, variant });
  };

  const hideToast = () => {
    setToastState((prev) => ({ ...prev, show: false }));
  };

  return {
    ...toastState,
    showToast,
    hideToast,
  };
}
