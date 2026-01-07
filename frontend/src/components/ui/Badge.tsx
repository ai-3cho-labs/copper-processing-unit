'use client';

import { cn } from '@/lib/cn';
import type { TierInfo } from '@/types/api';

export interface BadgeProps {
  /** Badge variant */
  variant?: 'default' | 'copper' | 'green' | 'gold' | 'red' | 'blue' | 'tier';
  /** Badge size */
  size?: 'sm' | 'md' | 'lg';
  /** Badge content */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

/**
 * Badge component with pixel art palette
 */
export function Badge({
  variant = 'default',
  size = 'md',
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        // Base styles
        'inline-flex items-center font-medium rounded-full',
        // Size variants
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-2.5 py-0.5 text-sm',
        size === 'lg' && 'px-3 py-1 text-sm',
        // Color variants (pixel palette)
        variant === 'default' && 'bg-bg-surface text-text-secondary',
        variant === 'copper' && 'bg-copper/20 text-copper',
        variant === 'green' && 'bg-pixel-green/20 text-pixel-green',
        variant === 'gold' && 'bg-pixel-gold/20 text-pixel-gold',
        variant === 'red' && 'bg-pixel-red/20 text-pixel-red',
        variant === 'blue' && 'bg-pixel-blue/20 text-pixel-blue',
        variant === 'tier' && 'bg-copper/10 text-copper border border-copper/30',
        className
      )}
    >
      {children}
    </span>
  );
}

/**
 * Tier badge component
 * Displays tier emoji and name
 */
export function TierBadge({
  tier,
  showMultiplier = false,
  size = 'md',
  className,
}: {
  tier: TierInfo;
  showMultiplier?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  return (
    <Badge variant="tier" size={size} className={className}>
      <span className="mr-1">{tier.emoji}</span>
      <span>{tier.name}</span>
      {showMultiplier && (
        <span className="ml-1 text-copper-dim">({tier.multiplier}x)</span>
      )}
    </Badge>
  );
}

/**
 * Rank badge component
 * Displays user rank with medal
 */
export function RankBadge({
  rank,
  size = 'md',
  className,
}: {
  rank: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  // Medal emoji for top 3
  const medal =
    rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : null;

  return (
    <Badge
      variant={rank <= 3 ? 'copper' : 'default'}
      size={size}
      className={className}
    >
      {medal && <span className="mr-1">{medal}</span>}
      <span>#{rank}</span>
    </Badge>
  );
}

/**
 * Status badge component
 */
export function StatusBadge({
  status,
  size = 'md',
  className,
}: {
  status: 'online' | 'offline' | 'pending' | 'success' | 'error';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const statusConfig = {
    online: { variant: 'green' as const, label: 'Online' },
    offline: { variant: 'default' as const, label: 'Offline' },
    pending: { variant: 'gold' as const, label: 'Pending' },
    success: { variant: 'green' as const, label: 'Success' },
    error: { variant: 'red' as const, label: 'Error' },
  };

  const { variant, label } = statusConfig[status];

  return (
    <Badge variant={variant} size={size} className={className}>
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full mr-1.5',
          variant === 'green' && 'bg-pixel-green',
          variant === 'gold' && 'bg-pixel-gold',
          variant === 'red' && 'bg-pixel-red',
          variant === 'default' && 'bg-text-muted'
        )}
      />
      {label}
    </Badge>
  );
}
