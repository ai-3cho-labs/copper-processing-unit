'use client';

import { cn } from '@/lib/cn';

export interface ProgressBarProps {
  /** Progress value (0-100) */
  value: number;
  /** Maximum value (default: 100) */
  max?: number;
  /** Show percentage label */
  showLabel?: boolean;
  /** Custom label */
  label?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Color variant */
  variant?: 'copper' | 'green' | 'amber' | 'gradient';
  /** Additional class names */
  className?: string;
}

/**
 * Progress bar component
 * Desktop: ASCII-style progress bar
 * Mobile: Modern progress bar
 */
export function ProgressBar({
  value,
  max = 100,
  showLabel = false,
  label,
  size = 'md',
  variant = 'copper',
  className,
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  // Size classes
  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  };

  // Color classes for the fill
  const fillClasses = {
    copper: 'bg-copper',
    green: 'bg-terminal-green',
    amber: 'bg-terminal-amber',
    gradient: 'bg-gradient-to-r from-copper-dim via-copper to-copper-glow',
  };

  return (
    <div className={cn('w-full', className)}>
      {/* Label */}
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-1">
          {label && (
            <span className="text-xs text-zinc-500 font-mono">{label}</span>
          )}
          {showLabel && (
            <span className="text-xs text-zinc-400 font-mono">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}

      {/* Progress track */}
      <div
        className={cn(
          'w-full rounded-full overflow-hidden',
          'bg-terminal-border',
          sizeClasses[size]
        )}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        {/* Progress fill */}
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300 ease-out',
            fillClasses[variant]
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

/**
 * ASCII-style progress bar (desktop only)
 * Shows progress like: [████████░░░░░░░░] 50%
 */
export function AsciiProgressBar({
  value,
  max = 100,
  width = 20,
  variant = 'copper',
  className,
}: {
  value: number;
  max?: number;
  width?: number;
  variant?: 'copper' | 'green' | 'amber';
  className?: string;
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  const filled = Math.round((percentage / 100) * width);
  const empty = width - filled;

  const filledChars = '█'.repeat(filled);
  const emptyChars = '░'.repeat(empty);

  const variantClasses = {
    copper: 'text-copper',
    green: 'text-pixel-green',
    amber: 'text-terminal-amber',
  };

  return (
    <span className={cn('font-mono text-sm whitespace-pre', className)}>
      <span className="text-terminal-border">[</span>
      <span className={variantClasses[variant]}>{filledChars}</span>
      <span className="text-terminal-muted">{emptyChars}</span>
      <span className="text-terminal-border">]</span>
      <span className="text-zinc-500 ml-2">{Math.round(percentage)}%</span>
    </span>
  );
}
