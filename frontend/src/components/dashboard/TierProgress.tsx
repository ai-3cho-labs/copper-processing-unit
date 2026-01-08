'use client';

import { cn } from '@/lib/cn';
import { formatDuration, formatMultiplier } from '@/lib/utils';
import type { TierInfo } from '@/types/api';
import { TIER_CONFIG, type TierId } from '@/types/models';
import {
  TerminalCard,
  ProgressBar,
  AsciiProgressBar,
  Skeleton,
} from '@/components/ui';

export interface TierProgressProps {
  /** Current tier info */
  tier: TierInfo;
  /** Next tier info (null if at max) */
  nextTier: TierInfo | null;
  /** Current streak in hours */
  streakHours: number;
  /** Progress percentage to next tier (0-100) */
  progress: number;
  /** Hours until next tier */
  hoursToNextTier: number | null;
  /** Is data loading */
  isLoading?: boolean;
  /** Show all tiers timeline */
  showAllTiers?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * TierProgress - Visual tier progression with streak display
 */
export function TierProgress({
  tier,
  nextTier,
  streakHours,
  progress,
  hoursToNextTier,
  isLoading = false,
  showAllTiers = false,
  className,
}: TierProgressProps) {
  if (isLoading) {
    return <TierProgressSkeleton className={className} />;
  }

  const isMaxTier = !nextTier;
  const streakDays = Math.floor(streakHours / 24);

  return (
    <TerminalCard title="TIER PROGRESS" className={className}>
      <div className="space-y-4">
        {/* Current Tier Display */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{tier.emoji}</span>
            <div>
              <div className="font-medium text-zinc-100 lg:font-mono">
                {tier.name}
              </div>
              <div className="text-xs text-zinc-500">
                {formatMultiplier(tier.multiplier)} multiplier
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-white lg:font-mono">
              {streakDays}d streak
            </div>
            <div className="text-xs text-zinc-500">
              {formatDuration(streakHours)} total
            </div>
          </div>
        </div>

        {/* Progress to Next Tier */}
        {!isMaxTier && nextTier && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-500 lg:font-mono lg:text-gray-500">
                Progress to {nextTier.name}
              </span>
              <span className="text-zinc-400 lg:font-mono">
                {hoursToNextTier !== null && hoursToNextTier > 0
                  ? `${formatDuration(hoursToNextTier)} remaining`
                  : 'Ready!'}
              </span>
            </div>

            {/* Desktop: ASCII progress bar */}
            <div className="hidden lg:block">
              <AsciiProgressBar
                value={progress}
              />
            </div>

            {/* Mobile: Standard progress bar */}
            <div className="lg:hidden">
              <ProgressBar
                value={progress}
                variant="default"
                showLabel
                size="md"
              />
            </div>
          </div>
        )}

        {/* Max Tier Message */}
        {isMaxTier && (
          <div className="text-center py-2 px-4 rounded bg-white/10 border border-white/20">
            <span className="text-sm text-white lg:font-mono">
              Maximum tier achieved! Enjoying {formatMultiplier(tier.multiplier)}{' '}
              bonus
            </span>
          </div>
        )}

        {/* All Tiers Timeline (optional) */}
        {showAllTiers && <TierTimeline currentTier={tier.tier as TierId} />}
      </div>
    </TerminalCard>
  );
}

/**
 * Tier timeline showing all tiers
 */
function TierTimeline({ currentTier }: { currentTier: TierId }) {
  const tiers = Object.entries(TIER_CONFIG) as [string, (typeof TIER_CONFIG)[TierId]][];

  return (
    <div className="pt-3 border-t border-zinc-800 lg:border-terminal-border">
      <div className="text-xs text-zinc-500 mb-2 lg:font-mono lg:text-gray-500">
        TIER PROGRESSION
      </div>
      <div className="flex items-center gap-1">
        {tiers.map(([id, config], index) => {
          const tierId = parseInt(id) as TierId;
          const isActive = tierId === currentTier;
          const isPast = tierId < currentTier;

          return (
            <div key={id} className="flex items-center">
              {/* Tier node */}
              <div
                className={cn(
                  'relative flex items-center justify-center',
                  'w-8 h-8 rounded-full text-sm',
                  'transition-all duration-200',
                  isActive && 'bg-white/20 ring-2 ring-white scale-110',
                  isPast && 'bg-white/20',
                  !isActive && !isPast && 'bg-zinc-800'
                )}
                title={`${config.name} (${formatMultiplier(config.multiplier)})`}
              >
                <span className={cn(isActive ? 'text-lg' : 'text-sm')}>
                  {config.emoji}
                </span>
              </div>

              {/* Connector line */}
              {index < tiers.length - 1 && (
                <div
                  className={cn(
                    'w-3 h-0.5 sm:w-4',
                    isPast ? 'bg-white/50' : 'bg-zinc-700'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Loading skeleton
 */
function TierProgressSkeleton({ className }: { className?: string }) {
  return (
    <TerminalCard title="TIER PROGRESS" className={className}>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="w-10 h-10 rounded-full" />
            <div className="space-y-1.5">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
          <div className="text-right space-y-1.5">
            <Skeleton className="h-4 w-16 ml-auto" />
            <Skeleton className="h-3 w-12 ml-auto" />
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-20" />
          </div>
          <Skeleton className="h-2.5 w-full rounded-full" />
        </div>
      </div>
    </TerminalCard>
  );
}
