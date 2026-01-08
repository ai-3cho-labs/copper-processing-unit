'use client';

import { useWalletAddress } from '@/hooks/useWallet';
import { useUserStats, usePoolStatus } from '@/hooks/api';
import { formatCompactNumber, formatMultiplier } from '@/lib/utils';
import { cn } from '@/lib/cn';
import { PixelMiner } from './PixelMiner';
import { MineTilemap } from './MineTilemap';
import { Skeleton } from '@/components/ui/Skeleton';

// Animation delay classes for staggered entrance
const animationDelays = [
  'animate-fade-slide-in',
  'animate-fade-slide-in [animation-delay:100ms]',
  'animate-fade-slide-in [animation-delay:200ms]',
  'animate-fade-slide-in [animation-delay:300ms]',
];

interface MinerDisplayProps {
  onViewDetails: () => void;
  className?: string;
}

interface StatBadgeProps {
  label: string;
  value: string;
  subtext?: string;
  glow?: boolean;
  className?: string;
}

function StatBadge({ label, value, subtext, glow, className }: StatBadgeProps) {
  return (
    <div className={cn('text-center', className)}>
      <div className="text-[10px] text-gray-400 uppercase tracking-widest font-medium mb-2">
        {label}
      </div>
      <div
        className={cn(
          'text-xl sm:text-2xl lg:text-3xl font-bold font-mono leading-none',
          glow
            ? 'text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.5)]'
            : 'text-white'
        )}
      >
        {value}
      </div>
      {subtext && (
        <div className={cn(
          'text-xs mt-1.5 font-medium',
          glow ? 'text-amber-400/70' : 'text-gray-500'
        )}>
          {subtext}
        </div>
      )}
    </div>
  );
}

function StatBadgeSkeleton() {
  return (
    <div className="text-center">
      <Skeleton className="h-2.5 w-14 mx-auto mb-3" />
      <Skeleton className="h-8 w-16 mx-auto" />
      <Skeleton className="h-3 w-10 mx-auto mt-2" />
    </div>
  );
}

// Desktop card styles
const cardBaseStyles = cn(
  'relative overflow-hidden rounded-xl px-6 py-5',
  'bg-gradient-to-b from-white/[0.08] to-white/[0.02]',
  'border border-white/10',
  'backdrop-blur-sm',
  'transition-all duration-300',
  'hover:border-white/20 hover:from-white/[0.12] hover:to-white/[0.04]',
  'hover:scale-[1.02] hover:shadow-lg hover:shadow-black/20'
);

const glowCardStyles = cn(
  'relative overflow-hidden rounded-xl px-6 py-5',
  'bg-gradient-to-b from-amber-500/10 to-amber-500/[0.02]',
  'border border-amber-500/20',
  'backdrop-blur-sm',
  'transition-all duration-300',
  'hover:border-amber-500/40 hover:from-amber-500/15 hover:to-amber-500/[0.05]',
  'hover:scale-[1.02] hover:shadow-lg hover:shadow-amber-500/10'
);

// Mobile card styles
const mobileCardStyles = cn(
  'rounded-2xl px-4 py-4',
  'bg-gradient-to-b from-white/[0.06] to-white/[0.02]',
  'border border-white/10',
  'transition-all duration-200',
  'active:scale-[0.98] active:bg-white/[0.08]'
);

const mobileGlowCardStyles = cn(
  'rounded-2xl px-4 py-4',
  'bg-gradient-to-b from-amber-500/10 to-amber-500/[0.02]',
  'border border-amber-500/20',
  'transition-all duration-200',
  'active:scale-[0.98] active:bg-amber-500/15'
);

const mobileTierCardStyles = cn(
  'rounded-2xl px-6 py-5',
  'bg-gradient-to-b from-white/[0.08] to-white/[0.03]',
  'border border-white/15',
  'shadow-lg shadow-black/20'
);

/**
 * Main dashboard centerpiece with animated pixel miner and 4 core stats.
 * Stats: Balance, Hash Power, Tier, Pending Reward
 */
export function MinerDisplay({ onViewDetails, className }: MinerDisplayProps) {
  const wallet = useWalletAddress();
  const { data: stats, isLoading: statsLoading } = useUserStats(wallet);
  const { data: pool, isLoading: poolLoading } = usePoolStatus();

  const isLoading = statsLoading || poolLoading;

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center min-h-[60vh] px-4',
        className
      )}
    >
      {/* Desktop Layout */}
      <div className="hidden lg:flex flex-col items-center gap-6">
        {/* Mine Tilemap with Miner */}
        <MineTilemap scale={4} minerPosition={{ x: 0.5, y: 1.8 }}>
          <PixelMiner scale={4} animation="drilling" frameTime={150} />
        </MineTilemap>

        {/* Stats Cards */}
        <div className="flex items-stretch gap-3">
          {isLoading ? (
            <>
              <div className={cardBaseStyles}>
                <StatBadgeSkeleton />
              </div>
              <div className={cardBaseStyles}>
                <StatBadgeSkeleton />
              </div>
              <div className={glowCardStyles}>
                <StatBadgeSkeleton />
              </div>
              <div className={glowCardStyles}>
                <StatBadgeSkeleton />
              </div>
            </>
          ) : (
            <>
              <div className={cn(cardBaseStyles, animationDelays[0])}>
                <StatBadge
                  label="Tier"
                  value={stats?.tier.emoji ?? '🪨'}
                  subtext={stats?.tier.name}
                />
              </div>
              <div className={cn(cardBaseStyles, animationDelays[1])}>
                <StatBadge
                  label="Balance"
                  value={formatCompactNumber(stats?.balance ?? 0)}
                  subtext="$CPU"
                />
              </div>
              <div className={cn(glowCardStyles, animationDelays[2])}>
                <StatBadge
                  label="Hash Power"
                  value={formatCompactNumber(stats?.hashPower ?? 0)}
                  subtext="H/s"
                  glow
                />
              </div>
              <div className={cn(glowCardStyles, animationDelays[3])}>
                <StatBadge
                  label="Pending"
                  value={`+${formatCompactNumber(stats?.pendingReward ?? 0)}`}
                  subtext="$CPU"
                  glow
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Mobile Layout */}
      <div className="lg:hidden flex flex-col items-center gap-5 w-full max-w-sm">
        {/* Tier Card on top */}
        {isLoading ? (
          <div className={mobileTierCardStyles}>
            <StatBadgeSkeleton />
          </div>
        ) : (
          <div className={cn(mobileTierCardStyles, animationDelays[0])}>
            <StatBadge
              label="Tier"
              value={stats?.tier.emoji ?? '🪨'}
              subtext={`${stats?.tier.name} (${formatMultiplier(stats?.multiplier ?? 1)})`}
            />
          </div>
        )}

        {/* Mine Tilemap with Miner */}
        <MineTilemap scale={2.5} minerPosition={{ x: 0.5, y: 1.8 }}>
          <PixelMiner scale={2.5} animation="drilling" frameTime={150} />
        </MineTilemap>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 w-full">
          {isLoading ? (
            <>
              <div className={mobileCardStyles}><StatBadgeSkeleton /></div>
              <div className={mobileGlowCardStyles}><StatBadgeSkeleton /></div>
              <div className={mobileCardStyles}><StatBadgeSkeleton /></div>
              <div className={mobileGlowCardStyles}><StatBadgeSkeleton /></div>
            </>
          ) : (
            <>
              <div className={cn(mobileCardStyles, animationDelays[0])}>
                <StatBadge
                  label="Balance"
                  value={formatCompactNumber(stats?.balance ?? 0)}
                  subtext="$CPU"
                />
              </div>
              <div className={cn(mobileGlowCardStyles, animationDelays[1])}>
                <StatBadge
                  label="Hash Power"
                  value={formatCompactNumber(stats?.hashPower ?? 0)}
                  subtext="H/s"
                  glow
                />
              </div>
              <div className={cn(mobileCardStyles, animationDelays[2])}>
                <StatBadge
                  label="Rank"
                  value={stats?.rank ? `#${stats.rank}` : '-'}
                  subtext="Leaderboard"
                />
              </div>
              <div className={cn(mobileGlowCardStyles, animationDelays[3])}>
                <StatBadge
                  label="Pending"
                  value={`+${formatCompactNumber(stats?.pendingReward ?? 0)}`}
                  subtext="$CPU"
                  glow
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* View Details Button */}
      <button
        onClick={onViewDetails}
        className={cn(
          'mt-6 px-8 py-3.5 rounded-xl text-sm font-medium',
          'bg-white/10 text-white',
          'border border-white/20',
          'transition-all duration-200',
          // Desktop hover
          'lg:hover:bg-white/20 lg:hover:border-white/40',
          // Mobile active
          'active:scale-[0.98] active:bg-white/20'
        )}
      >
        View Details
      </button>

      {/* Pool status hint */}
      {!isLoading && pool && (
        <div className={cn(
          'mt-4 px-4 py-2 rounded-full text-xs text-center',
          'bg-white/5 border border-white/10',
          pool.thresholdMet && 'border-amber-500/30 bg-amber-500/10'
        )}>
          <span className="text-gray-400">Pool:</span>{' '}
          <span className="text-white font-medium">
            {pool.progressToThreshold.toFixed(0)}%
          </span>
          <span className="text-gray-500"> to payout</span>
          {pool.thresholdMet && (
            <span className="ml-2 text-amber-400 font-medium animate-pulse">
              READY
            </span>
          )}
        </div>
      )}
    </div>
  );
}
