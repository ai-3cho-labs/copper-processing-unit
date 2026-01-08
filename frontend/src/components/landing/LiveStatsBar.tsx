'use client';

import { cn } from '@/lib/cn';
import { formatCompactNumber, formatUSD } from '@/lib/utils';
import { Skeleton } from '@/components/ui';
import { useCountdown } from '@/hooks/useCountdown';

export interface LiveStatsBarProps {
  /** Total holders */
  holders: number;
  /** 24h volume (USD) */
  volume24h: number;
  /** Pool value (USD) */
  poolValueUsd: number;
  /** Hours until next distribution */
  hoursUntilNext: number | null;
  /** Is loading */
  isLoading?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * LiveStatsBar - Real-time ticker of global stats
 */
export function LiveStatsBar({
  holders,
  volume24h,
  poolValueUsd,
  hoursUntilNext,
  isLoading = false,
  className,
}: LiveStatsBarProps) {
  const countdown = useCountdown(hoursUntilNext);

  if (isLoading) {
    return <LiveStatsBarSkeleton className={className} />;
  }

  return (
    <div
      className={cn(
        'w-full py-3 px-4',
        // Desktop: Terminal style
        'lg:bg-terminal-card lg:border-y lg:border-terminal-border',
        // Mobile: Clean style
        'bg-zinc-900/50 border-y border-zinc-800',
        className
      )}
    >
      <div className="max-w-6xl mx-auto">
        {/* Desktop Layout - Horizontal */}
        <div className="hidden lg:flex items-center justify-center gap-8 font-mono text-sm">
          <StatItem
            label="MINERS"
            value={formatCompactNumber(holders)}
          />
          <Divider />
          <StatItem
            label="24H VOLUME"
            value={formatUSD(volume24h, true)}
          />
          <Divider />
          <StatItem
            label="POOL"
            value={formatUSD(poolValueUsd)}
            highlight={poolValueUsd >= 250}
          />
          <Divider />
          <StatItem
            label="NEXT DROP"
            value={countdown.formatted}
            highlight={countdown.isComplete}
          />
        </div>

        {/* Mobile Layout - 2x2 Grid */}
        <div className="lg:hidden grid grid-cols-4 gap-2">
          <MobileStatItem label="Miners" value={formatCompactNumber(holders)} />
          <MobileStatItem label="Volume" value={formatUSD(volume24h, true)} />
          <MobileStatItem
            label="Pool"
            value={formatUSD(poolValueUsd)}
            highlight={poolValueUsd >= 250}
          />
          <MobileStatItem
            label="Next"
            value={countdown.formattedCompact}
            highlight={countdown.isComplete}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Desktop stat item
 * Monochrome design
 */
function StatItem({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div
        className={cn(
          'tabular-nums',
          highlight ? 'text-white glow-white' : 'text-gray-200'
        )}
      >
        {value}
      </div>
    </div>
  );
}

/**
 * Mobile stat item
 * Monochrome design
 */
function MobileStatItem({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="text-center">
      <div
        className={cn(
          'text-sm font-medium tabular-nums',
          highlight ? 'text-white glow-white' : 'text-gray-200'
        )}
      >
        {value}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

/**
 * Vertical divider
 */
function Divider() {
  return <div className="w-px h-8 bg-gray-700" />;
}

/**
 * Loading skeleton
 */
function LiveStatsBarSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'w-full py-3 px-4',
        'lg:bg-terminal-card lg:border-y lg:border-terminal-border',
        'bg-zinc-900/50 border-y border-zinc-800',
        className
      )}
    >
      <div className="max-w-6xl mx-auto">
        {/* Desktop */}
        <div className="hidden lg:flex items-center justify-center gap-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-8">
              <div className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-5 w-20" />
              </div>
              {i < 4 && <div className="w-px h-8 bg-terminal-border" />}
            </div>
          ))}
        </div>
        {/* Mobile */}
        <div className="lg:hidden grid grid-cols-4 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="text-center space-y-1">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-3 w-8 mx-auto" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
