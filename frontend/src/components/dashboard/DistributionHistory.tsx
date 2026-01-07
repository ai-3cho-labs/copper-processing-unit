'use client';

import Link from 'next/link';
import { cn } from '@/lib/cn';
import {
  formatCompactNumber,
  formatCOPPER,
  formatPercent,
} from '@/lib/utils';
import { TerminalCard, Skeleton } from '@/components/ui';

export interface DistributionHistoryItem {
  /** Distribution ID */
  id: string;
  /** Amount received by user */
  amount: number;
  /** User's hash power at time */
  hashPower: number;
  /** User's share percentage */
  sharePercent: number;
  /** Distribution timestamp */
  distributedAt: Date;
  /** Relative time */
  timeAgo: string;
  /** Transaction signature */
  txSignature?: string;
}

export interface DistributionHistoryProps {
  /** Distribution history items */
  history: DistributionHistoryItem[] | null;
  /** Is data loading */
  isLoading?: boolean;
  /** Max items to show */
  limit?: number;
  /** Show "View All" link */
  showViewAll?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * DistributionHistory - User's distribution receipts
 */
export function DistributionHistory({
  history,
  isLoading = false,
  limit = 5,
  showViewAll = true,
  className,
}: DistributionHistoryProps) {
  if (isLoading) {
    return <DistributionHistorySkeleton limit={limit} className={className} />;
  }

  const displayHistory = history?.slice(0, limit) ?? [];
  const totalReceived = history?.reduce((sum, item) => sum + item.amount, 0) ?? 0;

  return (
    <TerminalCard
      title="DISTRIBUTION HISTORY"
      className={className}
      headerRight={
        showViewAll && (
          <Link
            href="/history"
            className="text-xs text-copper hover:text-copper-glow transition-colors lg:font-mono"
          >
            View All →
          </Link>
        )
      }
    >
      <div className="space-y-2">
        {displayHistory.length > 0 ? (
          <>
            {/* Desktop Table Header */}
            <div className="hidden lg:grid grid-cols-12 gap-2 px-2 py-1 text-xs font-mono text-copper-dim border-b border-terminal-border">
              <div className="col-span-3">DATE</div>
              <div className="col-span-3 text-right">AMOUNT</div>
              <div className="col-span-3 text-right">HASH PWR</div>
              <div className="col-span-3 text-right">SHARE</div>
            </div>

            {/* History Items */}
            {displayHistory.map((item) => (
              <DistributionRow key={item.id} item={item} />
            ))}

            {/* Total Summary */}
            {history && history.length > 0 && (
              <div className="pt-2 mt-2 border-t border-zinc-800 lg:border-terminal-border">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-zinc-500 lg:font-mono lg:text-copper-dim">
                    Total Received
                  </span>
                  <span className="font-medium text-terminal-green lg:font-mono">
                    {formatCOPPER(totalReceived, true)}
                  </span>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-6 text-zinc-500">
            <div className="text-2xl mb-2">📋</div>
            <p className="text-sm">No distributions yet</p>
            <p className="text-xs text-zinc-600 mt-1">
              Hold your tokens to receive distributions
            </p>
          </div>
        )}
      </div>
    </TerminalCard>
  );
}

/**
 * Single distribution row
 */
function DistributionRow({ item }: { item: DistributionHistoryItem }) {
  const solscanUrl = item.txSignature
    ? `https://solscan.io/tx/${item.txSignature}`
    : null;

  const content = (
    <>
      {/* Desktop Layout */}
      <div className="hidden lg:grid grid-cols-12 gap-2 items-center font-mono text-sm">
        <div className="col-span-3 text-zinc-400">{item.timeAgo}</div>
        <div className="col-span-3 text-right text-terminal-green">
          +{formatCompactNumber(item.amount)}
        </div>
        <div className="col-span-3 text-right text-zinc-400">
          {formatCompactNumber(item.hashPower)}
        </div>
        <div className="col-span-3 text-right text-copper">
          {formatPercent(item.sharePercent, 2)}
        </div>
      </div>

      {/* Mobile Layout */}
      <div className="lg:hidden">
        <div className="flex items-center justify-between">
          <span className="text-terminal-green font-medium">
            +{formatCompactNumber(item.amount)} $COPPER
          </span>
          <span className="text-xs text-zinc-500">{item.timeAgo}</span>
        </div>
        <div className="flex items-center justify-between text-xs text-zinc-500 mt-0.5">
          <span>HP: {formatCompactNumber(item.hashPower)}</span>
          <span>Share: {formatPercent(item.sharePercent, 2)}</span>
        </div>
      </div>
    </>
  );

  if (solscanUrl) {
    return (
      <a
        href={solscanUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          'block px-2 py-1.5 -mx-1 rounded',
          'transition-colors hover:bg-zinc-800/50'
        )}
      >
        {content}
      </a>
    );
  }

  return <div className="px-2 py-1.5 -mx-1">{content}</div>;
}

/**
 * Loading skeleton
 */
function DistributionHistorySkeleton({
  limit = 5,
  className,
}: {
  limit?: number;
  className?: string;
}) {
  return (
    <TerminalCard title="DISTRIBUTION HISTORY" className={className}>
      <div className="space-y-2">
        {/* Desktop header skeleton */}
        <div className="hidden lg:flex justify-between px-2 py-1 border-b border-terminal-border">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-20" />
        </div>

        {/* Row skeletons */}
        {Array.from({ length: limit }).map((_, i) => (
          <div key={i} className="px-2 py-1.5">
            {/* Desktop */}
            <div className="hidden lg:grid grid-cols-12 gap-2">
              <div className="col-span-3">
                <Skeleton className="h-4 w-16" />
              </div>
              <div className="col-span-3 flex justify-end">
                <Skeleton className="h-4 w-20" />
              </div>
              <div className="col-span-3 flex justify-end">
                <Skeleton className="h-4 w-16" />
              </div>
              <div className="col-span-3 flex justify-end">
                <Skeleton className="h-4 w-12" />
              </div>
            </div>
            {/* Mobile */}
            <div className="lg:hidden space-y-1">
              <div className="flex justify-between">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-4 w-12" />
              </div>
              <div className="flex justify-between">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </TerminalCard>
  );
}
