'use client';

import { cn } from '@/lib/cn';
import { TerminalCard } from './TerminalCard';
import { Button } from './Button';
import { getErrorMessage } from '@/lib/api';

export interface ErrorDisplayProps {
  /** Error title */
  title?: string;
  /** Error message or Error object */
  error: string | Error | unknown;
  /** Retry callback */
  onRetry?: () => void;
  /** Additional class names */
  className?: string;
  /** Compact mode (no card wrapper) */
  compact?: boolean;
}

/**
 * Error display component
 * Shows error message with optional retry button
 */
export function ErrorDisplay({
  title = 'Error',
  error,
  onRetry,
  className,
  compact = false,
}: ErrorDisplayProps) {
  const message = typeof error === 'string' ? error : getErrorMessage(error);

  const content = (
    <div className={cn('text-center py-4', className)}>
      {/* Error icon (ASCII style) */}
      <div className="text-terminal-red font-mono text-2xl mb-3" aria-hidden>
        [!]
      </div>

      {/* Title */}
      <h3 className="text-lg font-semibold text-zinc-200 mb-2">{title}</h3>

      {/* Message */}
      <p className="text-sm text-zinc-400 mb-4 max-w-md mx-auto">{message}</p>

      {/* Retry button */}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try Again
        </Button>
      )}
    </div>
  );

  if (compact) {
    return content;
  }

  return (
    <TerminalCard variant="error" className={className}>
      {content}
    </TerminalCard>
  );
}

/**
 * Inline error message
 */
export function ErrorInline({
  message,
  className,
}: {
  message: string;
  className?: string;
}) {
  return (
    <p
      className={cn(
        'text-sm text-terminal-red font-mono flex items-center gap-1',
        className
      )}
    >
      <span>[!]</span>
      <span>{message}</span>
    </p>
  );
}

/**
 * Error boundary fallback
 */
export function ErrorFallback({
  error,
  resetErrorBoundary,
}: {
  error: Error;
  resetErrorBoundary?: () => void;
}) {
  return (
    <div className="min-h-[50vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <TerminalCard variant="error" title="Something went wrong">
          <div className="text-center py-4">
            <p className="text-sm text-zinc-400 mb-4">
              {error.message || 'An unexpected error occurred'}
            </p>
            {resetErrorBoundary && (
              <Button variant="outline" onClick={resetErrorBoundary}>
                Try Again
              </Button>
            )}
          </div>
        </TerminalCard>
      </div>
    </div>
  );
}
