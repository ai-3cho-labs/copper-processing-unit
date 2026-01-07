'use client';

import { formatUSD, formatCompactNumber } from '@/lib/utils';
import type { PoolInfo } from '@/types/models';
import { DISTRIBUTION_THRESHOLD_USD } from '@/types/models';
import {
  TerminalCard,
  ProgressBar,
  AsciiProgressBar,
  Skeleton,
} from '@/components/ui';
import { useCountdown, useAnimatedNumber } from '@/hooks/useCountdown';

export interface PendingRewardsProps {
  /** Estimated pending reward (COPPER tokens) */
  pendingReward: number;
  /** Pool information */
  pool: PoolInfo | null;
  /** Is data loading */
  isLoading?: boolean;
  /** Show compact version */
  compact?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * PendingRewards - Live counter showing pending reward with pool progress
 */
export function PendingRewards({
  pendingReward,
  pool,
  isLoading = false,
  compact = false,
  className,
}: PendingRewardsProps) {
  const animatedReward = useAnimatedNumber(pendingReward, 300);
  const countdown = useCountdown(pool?.hoursUntilTrigger ?? null);

  if (isLoading) {
    return <PendingRewardsSkeleton compact={compact} className={className} />;
  }

  if (compact) {
    return (
      <PendingRewardsCompact
        pendingReward={pendingReward}
        pool={pool}
        countdown={countdown}
        className={className}
      />
    );
  }

  return (
    <TerminalCard title="PENDING REWARDS" className={className}>
      <div className="space-y-4">
        {/* Pending Reward Amount */}
        <div className="text-center py-2">
          <div className="text-xs text-zinc-500 mb-1 lg:font-mono lg:text-copper-dim">
            YOUR ESTIMATED REWARD
          </div>
          <div className="text-3xl lg:text-4xl font-bold text-terminal-green lg:font-mono tabular-nums">
            +{formatCompactNumber(Math.floor(animatedReward))}
          </div>
          <div className="text-sm text-zinc-500 mt-1">$COPPER</div>
        </div>

        {/* Pool Progress */}
        {pool && (
          <div className="space-y-3">
            {/* Pool Value */}
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-500 lg:font-mono lg:text-copper-dim">
                Pool Value
              </span>
              <span className="font-medium text-zinc-100 lg:font-mono">
                {formatUSD(pool.valueUsd)} / {formatUSD(DISTRIBUTION_THRESHOLD_USD)}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="hidden lg:block">
              <AsciiProgressBar
                value={pool.progressToThreshold}
                variant={pool.thresholdMet ? 'green' : 'copper'}
              />
            </div>
            <div className="lg:hidden">
              <ProgressBar
                value={pool.progressToThreshold}
                variant={pool.thresholdMet ? 'green' : 'copper'}
                size="md"
              />
            </div>

            {/* Next Trigger Info */}
            <div className="flex items-center justify-between pt-2 border-t border-zinc-800 lg:border-terminal-border">
              <div className="text-xs text-zinc-500 lg:font-mono">
                {pool.nextTrigger === 'threshold'
                  ? 'Threshold trigger'
                  : pool.nextTrigger === 'time'
                    ? 'Time trigger'
                    : 'Next distribution'}
              </div>
              <CountdownDisplay countdown={countdown} pool={pool} />
            </div>
          </div>
        )}

        {/* Ready State */}
        {pool?.thresholdMet && (
          <div className="text-center py-2 px-4 rounded bg-terminal-green/10 border border-terminal-green/30">
            <span className="text-sm text-terminal-green lg:font-mono">
              Distribution threshold reached!
            </span>
          </div>
        )}
      </div>
    </TerminalCard>
  );
}

/**
 * Countdown display component
 */
function CountdownDisplay({
  countdown,
  pool,
}: {
  countdown: ReturnType<typeof useCountdown>;
  pool: PoolInfo;
}) {
  if (pool.thresholdMet || pool.timeTriggerMet) {
    return (
      <span className="text-sm font-medium text-terminal-green lg:font-mono">
        READY
      </span>
    );
  }

  return (
    <div className="text-right">
      {/* Desktop: Full countdown */}
      <span className="hidden lg:inline text-sm font-mono text-copper tabular-nums">
        {countdown.formatted}
      </span>
      {/* Mobile: Compact countdown */}
      <span className="lg:hidden text-sm font-medium text-copper">
        {countdown.formattedCompact}
      </span>
    </div>
  );
}

/**
 * Compact version for widgets
 */
function PendingRewardsCompact({
  pendingReward,
  pool,
  countdown,
  className,
}: {
  pendingReward: number;
  pool: PoolInfo | null;
  countdown: ReturnType<typeof useCountdown>;
  className?: string;
}) {
  return (
    <TerminalCard className={className}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-zinc-500">Pending</div>
          <div className="text-lg font-bold text-terminal-green tabular-nums">
            +{formatCompactNumber(pendingReward)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-zinc-500">Next drop</div>
          <div className="text-sm font-medium text-copper">
            {pool?.thresholdMet || pool?.timeTriggerMet
              ? 'READY'
              : countdown.formattedCompact}
          </div>
        </div>
      </div>
      {pool && (
        <div className="mt-2">
          <ProgressBar
            value={pool.progressToThreshold}
            variant={pool.thresholdMet ? 'green' : 'copper'}
            size="sm"
          />
        </div>
      )}
    </TerminalCard>
  );
}

/**
 * Loading skeleton
 */
function PendingRewardsSkeleton({
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
          <div className="space-y-1.5">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-6 w-20" />
          </div>
          <div className="space-y-1.5 text-right">
            <Skeleton className="h-3 w-14 ml-auto" />
            <Skeleton className="h-4 w-16 ml-auto" />
          </div>
        </div>
        <Skeleton className="h-1.5 w-full mt-2 rounded-full" />
      </TerminalCard>
    );
  }

  return (
    <TerminalCard title="PENDING REWARDS" className={className}>
      <div className="space-y-4">
        <div className="text-center py-2">
          <Skeleton className="h-3 w-32 mx-auto mb-2" />
          <Skeleton className="h-10 w-28 mx-auto" />
          <Skeleton className="h-4 w-16 mx-auto mt-1" />
        </div>
        <div className="space-y-3">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-2.5 w-full rounded-full" />
          <div className="flex justify-between pt-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
      </div>
    </TerminalCard>
  );
}
