'use client';

import { useState } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { PageContainer } from '@/components/layout';
import {
  TerminalCard,
  TierBadge,
  RankBadge,
  Button,
  Skeleton,
} from '@/components/ui';
import { useLeaderboard } from '@/hooks/api';
import { formatCompactNumber } from '@/lib/utils';
import { cn } from '@/lib/cn';
import type { LeaderboardUser } from '@/types/models';

const ITEMS_PER_PAGE = 25;

export default function LeaderboardPage() {
  const { publicKey } = useWallet();
  const wallet = publicKey?.toBase58() ?? null;
  const [limit, setLimit] = useState(ITEMS_PER_PAGE);

  const { data, isLoading, isFetching } = useLeaderboard(limit, wallet);

  const handleLoadMore = () => {
    setLimit((prev) => prev + ITEMS_PER_PAGE);
  };

  // Separate top 3 for mobile podium display
  const topThree = data?.slice(0, 3) ?? [];
  const restOfList = data?.slice(3) ?? [];

  return (
    <PageContainer>
      {/* Mobile Layout */}
      <div className="lg:hidden space-y-5">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-xl font-bold text-white">Leaderboard</h1>
          <p className="text-xs text-gray-500 mt-1">
            Top miners by Hash Power
          </p>
        </div>

        {/* Top 3 Podium */}
        {isLoading ? (
          <MobilePodiumSkeleton />
        ) : topThree.length > 0 ? (
          <MobilePodium entries={topThree} />
        ) : null}

        {/* Rest of leaderboard */}
        <div className="space-y-2">
          {isLoading ? (
            Array.from({ length: 7 }).map((_, i) => (
              <MobileRowSkeleton key={i} />
            ))
          ) : restOfList.length > 0 ? (
            restOfList.map((entry) => (
              <MobileRow key={entry.wallet} entry={entry} />
            ))
          ) : data?.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              <div className="text-3xl mb-2">🏆</div>
              <p className="text-sm">No miners yet</p>
              <p className="text-xs text-gray-600 mt-1">Be the first!</p>
            </div>
          ) : null}
        </div>

        {/* Load More */}
        {data && data.length >= limit && (
          <Button
            variant="outline"
            onClick={handleLoadMore}
            loading={isFetching}
            fullWidth
          >
            Load More
          </Button>
        )}
      </div>

      {/* Desktop Layout */}
      <div className="hidden lg:block space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-zinc-100 lg:font-mono">
            <span className="text-gray-500">&gt; </span>
            LEADERBOARD
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Top miners ranked by Hash Power (TWAB × Multiplier)
          </p>
        </div>

        {/* Leaderboard Table */}
        <TerminalCard noPadding>
          {/* Desktop Header */}
          <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b border-terminal-border font-mono text-sm text-gray-500">
            <div className="col-span-1">RANK</div>
            <div className="col-span-5">MINER</div>
            <div className="col-span-2 text-center">TIER</div>
            <div className="col-span-2 text-right">MULTIPLIER</div>
            <div className="col-span-2 text-right">HASH POWER</div>
          </div>

          {/* Rows */}
          <div className="divide-y divide-terminal-border/50">
            {isLoading ? (
              Array.from({ length: 10 }).map((_, i) => (
                <DesktopRowSkeleton key={i} />
              ))
            ) : data && data.length > 0 ? (
              data.map((entry) => (
                <DesktopRow key={entry.wallet} entry={entry} />
              ))
            ) : (
              <div className="px-4 py-12 text-center text-zinc-500">
                No miners on the leaderboard yet
              </div>
            )}
          </div>

          {/* Load More */}
          {data && data.length >= limit && (
            <div className="p-4 border-t border-terminal-border">
              <Button
                variant="outline"
                onClick={handleLoadMore}
                loading={isFetching}
                fullWidth
              >
                Load More
              </Button>
            </div>
          )}
        </TerminalCard>
      </div>
    </PageContainer>
  );
}

/**
 * Mobile Podium - Featured top 3 miners
 */
function MobilePodium({ entries }: { entries: LeaderboardUser[] }) {
  // Reorder for podium: 2nd, 1st, 3rd
  const ordered = [entries[1], entries[0], entries[2]].filter(Boolean);
  const heights = ['h-20', 'h-28', 'h-16'];
  const ranks = [2, 1, 3];

  return (
    <div className="flex items-end justify-center gap-2 px-2">
      {ordered.map((entry, idx) => (
        <div
          key={entry?.wallet ?? idx}
          className={cn(
            'flex-1 max-w-[120px] flex flex-col items-center',
            idx === 1 && 'order-2',
            idx === 0 && 'order-1',
            idx === 2 && 'order-3'
          )}
        >
          {entry && (
            <>
              {/* Tier emoji */}
              <span className="text-2xl mb-1">{entry.tier.emoji}</span>

              {/* Wallet */}
              <span
                className={cn(
                  'text-xs font-medium truncate max-w-full px-1',
                  entry.isCurrentUser ? 'text-white' : 'text-gray-300'
                )}
              >
                {entry.isCurrentUser ? 'You' : entry.walletShort}
              </span>

              {/* Hash Power */}
              <span className="text-[10px] text-gray-500 mb-2">
                {formatCompactNumber(entry.hashPower)} H/s
              </span>

              {/* Podium bar */}
              <div
                className={cn(
                  'w-full rounded-t-lg flex items-start justify-center pt-3',
                  heights[idx],
                  ranks[idx] === 1
                    ? 'bg-gradient-to-b from-amber-500/30 to-amber-500/10 border-t-2 border-x border-amber-500/40'
                    : ranks[idx] === 2
                    ? 'bg-gradient-to-b from-gray-400/20 to-gray-400/5 border-t-2 border-x border-gray-400/30'
                    : 'bg-gradient-to-b from-amber-700/20 to-amber-700/5 border-t-2 border-x border-amber-700/30'
                )}
              >
                <span
                  className={cn(
                    'text-lg font-bold',
                    ranks[idx] === 1
                      ? 'text-amber-400'
                      : ranks[idx] === 2
                      ? 'text-gray-300'
                      : 'text-amber-600'
                  )}
                >
                  #{ranks[idx]}
                </span>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}

function MobilePodiumSkeleton() {
  return (
    <div className="flex items-end justify-center gap-2 px-2">
      {[2, 1, 3].map((rank, idx) => (
        <div
          key={rank}
          className={cn(
            'flex-1 max-w-[120px] flex flex-col items-center',
            idx === 1 && 'order-2',
            idx === 0 && 'order-1',
            idx === 2 && 'order-3'
          )}
        >
          <Skeleton className="h-8 w-8 rounded-full mb-1" />
          <Skeleton className="h-3 w-16 mb-1" />
          <Skeleton className="h-2.5 w-12 mb-2" />
          <Skeleton
            className={cn(
              'w-full rounded-t-lg',
              rank === 1 ? 'h-28' : rank === 2 ? 'h-20' : 'h-16'
            )}
          />
        </div>
      ))}
    </div>
  );
}

/**
 * Mobile leaderboard row (ranks 4+)
 */
function MobileRow({ entry }: { entry: LeaderboardUser }) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-xl',
        'bg-white/[0.03] border border-white/5',
        'transition-all duration-200',
        'active:scale-[0.98] active:bg-white/[0.06]',
        entry.isCurrentUser && 'bg-white/[0.08] border-white/20'
      )}
    >
      {/* Rank */}
      <div className="w-10 flex-shrink-0">
        <span
          className={cn(
            'text-sm font-bold tabular-nums',
            entry.isCurrentUser ? 'text-white' : 'text-gray-400'
          )}
        >
          #{entry.rank}
        </span>
      </div>

      {/* Tier emoji */}
      <span className="text-xl flex-shrink-0">{entry.tier.emoji}</span>

      {/* Wallet + Multiplier */}
      <div className="flex-1 min-w-0">
        <div
          className={cn(
            'text-sm font-medium truncate',
            entry.isCurrentUser ? 'text-white' : 'text-gray-200'
          )}
        >
          {entry.isCurrentUser ? 'You' : entry.walletShort}
        </div>
        <div className="text-[10px] text-gray-500">
          {entry.tier.name} · {entry.multiplier.toFixed(1)}x
        </div>
      </div>

      {/* Hash Power */}
      <div className="text-right flex-shrink-0">
        <div
          className={cn(
            'text-sm font-bold tabular-nums',
            entry.isCurrentUser ? 'text-amber-400' : 'text-white'
          )}
        >
          {formatCompactNumber(entry.hashPower)}
        </div>
        <div className="text-[10px] text-gray-500">H/s</div>
      </div>
    </div>
  );
}

function MobileRowSkeleton() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5">
      <Skeleton className="h-4 w-8" />
      <Skeleton className="h-6 w-6 rounded-full" />
      <div className="flex-1">
        <Skeleton className="h-4 w-24 mb-1" />
        <Skeleton className="h-2.5 w-16" />
      </div>
      <div className="text-right">
        <Skeleton className="h-4 w-14 mb-1" />
        <Skeleton className="h-2.5 w-8 ml-auto" />
      </div>
    </div>
  );
}

/**
 * Desktop leaderboard row
 */
function DesktopRow({ entry }: { entry: LeaderboardUser }) {
  return (
    <div
      className={cn(
        'grid grid-cols-12 gap-4 px-4 py-3 items-center',
        'transition-colors hover:bg-zinc-800/30',
        entry.isCurrentUser && 'bg-white/10'
      )}
    >
      {/* Rank */}
      <div className="col-span-1">
        <RankBadge rank={entry.rank} size="sm" />
      </div>

      {/* Wallet */}
      <div className="col-span-5">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-sm font-mono',
              entry.isCurrentUser ? 'text-white font-medium' : 'text-zinc-300'
            )}
          >
            {entry.isCurrentUser ? 'You' : entry.walletShort}
          </span>
          {entry.isCurrentUser && (
            <span className="text-xs text-gray-500">(you)</span>
          )}
        </div>
      </div>

      {/* Tier */}
      <div className="col-span-2 flex justify-center">
        <TierBadge tier={entry.tier} size="sm" />
      </div>

      {/* Multiplier */}
      <div className="col-span-2 text-right">
        <span className="text-sm text-zinc-400 font-mono">
          {entry.multiplier.toFixed(1)}x
        </span>
      </div>

      {/* Hash Power */}
      <div className="col-span-2 text-right">
        <span
          className={cn(
            'text-sm font-medium tabular-nums font-mono',
            entry.isCurrentUser ? 'text-white glow-white' : 'text-white'
          )}
        >
          {formatCompactNumber(entry.hashPower)}
        </span>
      </div>
    </div>
  );
}

function DesktopRowSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center">
      <div className="col-span-1">
        <Skeleton className="h-6 w-10 rounded-full" />
      </div>
      <div className="col-span-5">
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="col-span-2 flex justify-center">
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <div className="col-span-2">
        <Skeleton className="h-5 w-10 ml-auto" />
      </div>
      <div className="col-span-2">
        <Skeleton className="h-5 w-16 ml-auto" />
      </div>
    </div>
  );
}
