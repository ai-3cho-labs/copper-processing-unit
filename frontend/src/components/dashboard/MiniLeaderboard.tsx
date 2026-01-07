'use client';

import Link from 'next/link';
import { cn } from '@/lib/cn';
import { formatCompactNumber } from '@/lib/utils';
import type { LeaderboardUser } from '@/types/models';
import {
  TerminalCard,
  RankBadge,
  Skeleton,
} from '@/components/ui';

export interface MiniLeaderboardProps {
  /** Leaderboard entries */
  entries: LeaderboardUser[] | null;
  /** Current user's rank (shown if not in entries) */
  userRank?: number | null;
  /** Current user's wallet */
  userWallet?: string | null;
  /** Is data loading */
  isLoading?: boolean;
  /** Show "View All" link */
  showViewAll?: boolean;
  /** Max entries to display */
  limit?: number;
  /** Additional class names */
  className?: string;
}

/**
 * MiniLeaderboard - Compact top miners display
 */
export function MiniLeaderboard({
  entries,
  userRank,
  userWallet,
  isLoading = false,
  showViewAll = true,
  limit = 5,
  className,
}: MiniLeaderboardProps) {
  if (isLoading) {
    return <MiniLeaderboardSkeleton limit={limit} className={className} />;
  }

  const displayEntries = entries?.slice(0, limit) ?? [];
  const userInTop = userWallet
    ? displayEntries.some((e) => e.wallet === userWallet)
    : false;

  return (
    <TerminalCard
      title="TOP MINERS"
      className={className}
      headerRight={
        showViewAll && (
          <Link
            href="/leaderboard"
            className="text-xs text-copper hover:text-copper-glow transition-colors lg:font-mono"
          >
            View All →
          </Link>
        )
      }
    >
      <div className="space-y-1">
        {/* Header Row - Desktop only */}
        <div className="hidden lg:grid grid-cols-12 gap-2 px-2 py-1 text-xs font-mono text-copper-dim border-b border-terminal-border">
          <div className="col-span-2">RANK</div>
          <div className="col-span-5">MINER</div>
          <div className="col-span-2 text-center">TIER</div>
          <div className="col-span-3 text-right">HASH PWR</div>
        </div>

        {/* Entries */}
        {displayEntries.length > 0 ? (
          displayEntries.map((entry) => (
            <LeaderboardRow
              key={entry.wallet}
              entry={entry}
              isCurrentUser={entry.wallet === userWallet}
            />
          ))
        ) : (
          <div className="text-center py-4 text-zinc-500 text-sm">
            No miners yet
          </div>
        )}

        {/* Current user if not in top */}
        {!userInTop && userRank && userRank > limit && (
          <>
            <div className="flex items-center justify-center py-1 text-zinc-600">
              <span className="text-xs lg:font-mono">• • •</span>
            </div>
            <div className="px-2 py-1.5 rounded bg-copper/5 border border-copper/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <RankBadge rank={userRank} size="sm" />
                  <span className="text-xs text-copper lg:font-mono">You</span>
                </div>
                <span className="text-xs text-zinc-500">
                  Keep holding to climb!
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </TerminalCard>
  );
}

/**
 * Single leaderboard row
 */
function LeaderboardRow({
  entry,
  isCurrentUser,
}: {
  entry: LeaderboardUser;
  isCurrentUser: boolean;
}) {
  return (
    <div
      className={cn(
        'grid grid-cols-12 gap-2 px-2 py-1.5 rounded items-center',
        'transition-colors',
        isCurrentUser
          ? 'bg-copper/10 border border-copper/20'
          : 'hover:bg-zinc-800/50'
      )}
    >
      {/* Rank */}
      <div className="col-span-2">
        <RankBadge rank={entry.rank} size="sm" />
      </div>

      {/* Wallet */}
      <div className="col-span-5 flex items-center gap-1.5 min-w-0">
        <span
          className={cn(
            'text-sm truncate',
            isCurrentUser ? 'text-copper font-medium' : 'text-zinc-300'
          )}
        >
          {isCurrentUser ? 'You' : entry.walletShort}
        </span>
      </div>

      {/* Tier */}
      <div className="col-span-2 flex justify-center">
        <span className="text-lg" title={entry.tier.name}>
          {entry.tier.emoji}
        </span>
      </div>

      {/* Hash Power */}
      <div className="col-span-3 text-right">
        <span
          className={cn(
            'text-sm tabular-nums lg:font-mono',
            isCurrentUser ? 'text-terminal-green' : 'text-zinc-400'
          )}
        >
          {formatCompactNumber(entry.hashPower)}
        </span>
      </div>
    </div>
  );
}

/**
 * Loading skeleton
 */
function MiniLeaderboardSkeleton({
  limit = 5,
  className,
}: {
  limit?: number;
  className?: string;
}) {
  return (
    <TerminalCard title="TOP MINERS" className={className}>
      <div className="space-y-1">
        {/* Header skeleton - desktop */}
        <div className="hidden lg:flex justify-between px-2 py-1 border-b border-terminal-border">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-3 w-16" />
        </div>

        {/* Row skeletons */}
        {Array.from({ length: limit }).map((_, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 px-2 py-1.5 items-center">
            <div className="col-span-2">
              <Skeleton className="h-5 w-8 rounded-full" />
            </div>
            <div className="col-span-5">
              <Skeleton className="h-4 w-20" />
            </div>
            <div className="col-span-2 flex justify-center">
              <Skeleton className="h-6 w-6 rounded-full" />
            </div>
            <div className="col-span-3 flex justify-end">
              <Skeleton className="h-4 w-14" />
            </div>
          </div>
        ))}
      </div>
    </TerminalCard>
  );
}
