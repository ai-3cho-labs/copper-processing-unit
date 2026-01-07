'use client';

import { cn } from '@/lib/cn';
import {
  formatCOPPER,
  formatCompactNumber,
  formatMultiplier,
} from '@/lib/utils';
import type { UserMiningStats } from '@/types/models';
import { TerminalCard, TierBadge, RankBadge, Skeleton } from '@/components/ui';

export interface MiningCardProps {
  /** User mining statistics */
  data: UserMiningStats | null;
  /** Is data loading */
  isLoading?: boolean;
  /** Show compact version */
  compact?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * MiningCard - Displays user's mining operation overview
 * Shows balance, TWAB, tier, hash power, and rank
 */
export function MiningCard({
  data,
  isLoading = false,
  compact = false,
  className,
}: MiningCardProps) {
  if (isLoading) {
    return <MiningCardSkeleton compact={compact} className={className} />;
  }

  if (!data) {
    return (
      <TerminalCard title="MINING STATUS" className={className}>
        <div className="text-center py-8 text-zinc-500">
          <p>No mining data available</p>
        </div>
      </TerminalCard>
    );
  }

  if (compact) {
    return <MiningCardCompact data={data} className={className} />;
  }

  return (
    <TerminalCard
      title="MINING STATUS"
      variant="highlight"
      className={className}
      headerRight={data.rank && <RankBadge rank={data.rank} size="sm" />}
    >
      <div className="space-y-4">
        {/* Balance Section */}
        <div className="space-y-1">
          <div className="flex items-baseline justify-between">
            <span className="text-xs text-zinc-500 lg:font-mono lg:text-gray-500">
              BALANCE
            </span>
            <TierBadge tier={data.tier} showMultiplier size="sm" />
          </div>
          <div className="text-2xl lg:text-3xl font-bold text-zinc-100 lg:font-mono lg:text-white tabular-nums">
            {formatCOPPER(data.balance, true)}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* TWAB */}
          <StatItem
            label="TWAB"
            value={formatCompactNumber(data.twab)}
            sublabel="Time-Weighted Avg"
          />

          {/* Hash Power */}
          <StatItem
            label="HASH POWER"
            value={formatCompactNumber(data.hashPower)}
            sublabel={`${formatMultiplier(data.multiplier)} multiplier`}
            highlight
          />
        </div>

        {/* Pending Reward Preview */}
        {data.pendingReward > 0 && (
          <div className="pt-3 border-t border-zinc-800 lg:border-terminal-border">
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-500 lg:font-mono lg:text-gray-500">
                PENDING REWARD
              </span>
              <span className="text-sm font-medium text-white glow-white lg:font-mono">
                +{formatCompactNumber(data.pendingReward)} $COPPER
              </span>
            </div>
          </div>
        )}
      </div>
    </TerminalCard>
  );
}

/**
 * Compact version for mobile or sidebar use
 */
function MiningCardCompact({
  data,
  className,
}: {
  data: UserMiningStats;
  className?: string;
}) {
  return (
    <TerminalCard className={className}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl">{data.tier.emoji}</div>
          <div>
            <div className="font-medium text-zinc-100">
              {formatCOPPER(data.balance, true)}
            </div>
            <div className="text-xs text-zinc-500">
              HP: {formatCompactNumber(data.hashPower)}
            </div>
          </div>
        </div>
        {data.rank && <RankBadge rank={data.rank} size="sm" />}
      </div>
    </TerminalCard>
  );
}

/**
 * Individual stat item
 */
function StatItem({
  label,
  value,
  sublabel,
  highlight = false,
}: {
  label: string;
  value: string;
  sublabel?: string;
  highlight?: boolean;
}) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs text-zinc-500 lg:font-mono lg:text-gray-500">
        {label}
      </div>
      <div
        className={cn(
          'text-lg font-semibold tabular-nums',
          highlight
            ? 'text-white glow-white'
            : 'text-zinc-100 lg:text-zinc-100'
        )}
      >
        {value}
      </div>
      {sublabel && (
        <div className="text-xs text-zinc-500 lg:text-zinc-600">{sublabel}</div>
      )}
    </div>
  );
}

/**
 * Loading skeleton
 */
function MiningCardSkeleton({
  compact = false,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  if (compact) {
    return (
      <TerminalCard className={className}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="w-10 h-10 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
          <Skeleton className="h-6 w-12 rounded-full" />
        </div>
      </TerminalCard>
    );
  }

  return (
    <TerminalCard title="MINING STATUS" className={className}>
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-24 rounded-full" />
          </div>
          <Skeleton className="h-8 w-40" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      </div>
    </TerminalCard>
  );
}
