'use client';

import { useState } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { PageContainer } from '@/components/layout';
import { WalletGuard } from '@/components/wallet/WalletGuard';
import {
  TerminalCard,
  Button,
  Skeleton,
  ConnectWalletEmpty,
} from '@/components/ui';
import { useUserHistory } from '@/hooks/api';
import {
  formatCompactNumber,
  formatCOPPER,
  formatTimeAgo,
  formatDateTime,
} from '@/lib/utils';
import type { DistributionHistoryItem } from '@/types/api';

const ITEMS_PER_PAGE = 20;

export default function HistoryPage() {
  return (
    <PageContainer>
      <WalletGuard
        notConnectedComponent={
          <div className="flex items-center justify-center min-h-[60vh]">
            <ConnectWalletEmpty />
          </div>
        }
      >
        <HistoryContent />
      </WalletGuard>
    </PageContainer>
  );
}

function HistoryContent() {
  const { publicKey } = useWallet();
  const wallet = publicKey?.toBase58() ?? null;
  const [limit, setLimit] = useState(ITEMS_PER_PAGE);

  const { data, isLoading, isFetching } = useUserHistory(wallet, limit);

  const handleLoadMore = () => {
    setLimit((prev) => prev + ITEMS_PER_PAGE);
  };

  // Calculate totals
  const totalReceived = data?.reduce((sum, item) => sum + item.amount_received, 0) ?? 0;
  const payoutCount = data?.length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold text-zinc-100 lg:font-mono">
          <span className="hidden lg:inline text-gray-500">&gt; </span>
          REWARD HISTORY
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          Your complete record of mining rewards
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <TerminalCard>
          <div className="text-center">
            <div className="text-xs text-zinc-500 mb-1 lg:font-mono lg:text-gray-500">
              TOTAL RECEIVED
            </div>
            <div className="text-xl lg:text-2xl font-bold text-white glow-white lg:font-mono tabular-nums">
              {formatCOPPER(totalReceived, true)}
            </div>
          </div>
        </TerminalCard>
        <TerminalCard>
          <div className="text-center">
            <div className="text-xs text-zinc-500 mb-1 lg:font-mono lg:text-gray-500">
              PAYOUTS
            </div>
            <div className="text-xl lg:text-2xl font-bold text-white lg:font-mono tabular-nums">
              {payoutCount}
            </div>
          </div>
        </TerminalCard>
      </div>

      {/* History Table */}
      <TerminalCard title="TRANSACTION HISTORY" noPadding>
        {/* Desktop Header */}
        <div className="hidden lg:grid grid-cols-12 gap-4 px-4 py-3 border-b border-terminal-border font-mono text-sm text-gray-500">
          <div className="col-span-3">DATE</div>
          <div className="col-span-3 text-right">AMOUNT</div>
          <div className="col-span-3 text-right">HASH POWER</div>
          <div className="col-span-3 text-right">TX</div>
        </div>

        {/* Rows */}
        <div className="divide-y divide-zinc-800 lg:divide-terminal-border/50">
          {isLoading ? (
            // Loading skeletons
            Array.from({ length: 5 }).map((_, i) => (
              <HistoryRowSkeleton key={i} />
            ))
          ) : data && data.length > 0 ? (
            data.map((item) => <HistoryRow key={item.distribution_id} item={item} />)
          ) : (
            <div className="px-4 py-12 text-center text-zinc-500">
              <div className="text-2xl mb-2">⛏️</div>
              <p>No rewards yet</p>
              <p className="text-xs text-zinc-600 mt-1">
                Hold tokens to earn mining rewards
              </p>
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
  );
}

function HistoryRow({ item }: { item: DistributionHistoryItem }) {
  const solscanUrl = item.tx_signature
    ? `https://solscan.io/tx/${item.tx_signature}`
    : null;
  const timeAgo = formatTimeAgo(item.executed_at);
  const dateTime = formatDateTime(item.executed_at);

  return (
    <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center hover:bg-zinc-800/30 transition-colors">
      {/* Date */}
      <div className="col-span-6 lg:col-span-3">
        <div className="text-sm text-zinc-300 lg:font-mono">{timeAgo}</div>
        <div className="text-xs text-zinc-500 lg:hidden">{dateTime}</div>
      </div>

      {/* Amount */}
      <div className="col-span-6 lg:col-span-3 text-right">
        <span className="text-sm font-medium text-white glow-white lg:font-mono tabular-nums">
          +{formatCompactNumber(item.amount_received)}
        </span>
        <span className="text-xs text-zinc-500 ml-1">$COPPER</span>
      </div>

      {/* Hash Power - Desktop */}
      <div className="hidden lg:block col-span-3 text-right">
        <span className="text-sm text-zinc-400 font-mono tabular-nums">
          {formatCompactNumber(item.hash_power)}
        </span>
      </div>

      {/* TX Link - Desktop */}
      <div className="hidden lg:block col-span-3 text-right">
        {solscanUrl ? (
          <a
            href={solscanUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-white hover:text-gray-300 transition-colors font-mono"
          >
            View TX ↗
          </a>
        ) : (
          <span className="text-xs text-zinc-600">-</span>
        )}
      </div>

      {/* Mobile: Additional info */}
      <div className="lg:hidden col-span-12 flex items-center justify-between text-xs text-zinc-500 -mt-1">
        <span>HP: {formatCompactNumber(item.hash_power)}</span>
        {solscanUrl && (
          <a
            href={solscanUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-white"
          >
            View TX ↗
          </a>
        )}
      </div>
    </div>
  );
}

function HistoryRowSkeleton() {
  return (
    <div className="grid grid-cols-12 gap-4 px-4 py-3 items-center">
      <div className="col-span-6 lg:col-span-3">
        <Skeleton className="h-5 w-20" />
      </div>
      <div className="col-span-6 lg:col-span-3 flex justify-end">
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="hidden lg:block col-span-3">
        <Skeleton className="h-5 w-16 ml-auto" />
      </div>
      <div className="hidden lg:block col-span-3">
        <Skeleton className="h-4 w-14 ml-auto" />
      </div>
    </div>
  );
}
