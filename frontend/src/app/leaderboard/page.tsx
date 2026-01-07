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

  return (
    <PageContainer>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-zinc-100 lg:font-mono">
            <span className="hidden lg:inline text-gray-500">&gt; </span>
            LEADERBOARD
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Top miners ranked by Hash Power (TWAB × Multiplier)
          </p>
        </div>

        {/* Leaderboard Table */}
        <TerminalCard noPadding>
          {/* Desktop Header */}
          <div className="hidden lg:grid grid-cols-12 gap-4 px-4 py-3 border-b border-terminal-border font-mono text-sm text-gray-500">
            <div className="col-span-1">RANK</div>
            <div className="col-span-5">MINER</div>
            <div className="col-span-2 text-center">TIER</div>
            <div className="col-span-2 text-right">MULTIPLIER</div>
            <div className="col-span-2 text-right">HASH POWER</div>
          </div>

          {/* Rows */}
          <div className="divide-y divide-zinc-800 lg:divide-terminal-border/50">
            {isLoading ? (
              // Loading skeletons
              Array.from({ length: 10 }).map((_, i) => (
                <LeaderboardRowSkeleton key={i} />
              ))
            ) : data && data.length > 0 ? (
              data.map((entry) => (
                <LeaderboardRow key={entry.wallet} entry={entry} />
              ))
            ) : (
              <div className="px-4 py-12 text-center text-zinc-500">
                No miners on the leaderboard yet
              </div>
            )}
          </div>

          {/* Load More */}
          {data && data.length >= limit && (
            <div className="p-4 border-t border-zinc-800 lg:border-terminal-border">
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

function LeaderboardRow({ entry }: { entry: LeaderboardUser }) {
  return (
    <div
      className={cn(
        'grid grid-cols-12 gap-4 px-4 py-3 items-center',
        'transition-colors hover:bg-zinc-800/30',
        entry.isCurrentUser && 'bg-white/10'
      )}
    >
      {/* Rank */}
      <div className="col-span-2 lg:col-span-1">
        <RankBadge rank={entry.rank} size="sm" />
      </div>

      {/* Wallet */}
      <div className="col-span-6 lg:col-span-5">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-sm lg:font-mono',
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

      {/* Tier - Desktop */}
      <div className="hidden lg:flex col-span-2 justify-center">
        <TierBadge tier={entry.tier} size="sm" />
      </div>

      {/* Multiplier - Desktop */}
      <div className="hidden lg:block col-span-2 text-right">
        <span className="text-sm text-zinc-400 lg:font-mono">
          {entry.multiplier.toFixed(1)}x
        </span>
      </div>

      {/* Hash Power */}
      <div className="col-span-4 lg:col-span-2 text-right">
        <span
          className={cn(
            'text-sm font-medium tabular-nums lg:font-mono',
            entry.isCurrentUser ? 'text-white glow-white' : 'text-white'
          )}
        >
          {formatCompactNumber(entry.hashPower)}
        </span>
      </div>

      {/* Mobile: Tier below */}
      <div className="lg:hidden col-span-12 -mt-2">
        <TierBadge tier={entry.tier} size="sm" showMultiplier />
      </div>
    </div>
  );
}

function LeaderboardRowSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center">
      <div className="col-span-2 lg:col-span-1">
        <Skeleton className="h-6 w-10 rounded-full" />
      </div>
      <div className="col-span-6 lg:col-span-5">
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="hidden lg:flex col-span-2 justify-center">
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <div className="hidden lg:block col-span-2">
        <Skeleton className="h-5 w-10 ml-auto" />
      </div>
      <div className="col-span-4 lg:col-span-2">
        <Skeleton className="h-5 w-16 ml-auto" />
      </div>
    </div>
  );
}
