'use client';

import { cn } from '@/lib/cn';
import {
  formatSOL,
  formatCompactNumber,
  formatUSD,
} from '@/lib/utils';
import type { FormattedBuyback } from '@/types/models';
import { TerminalCard, Skeleton, Badge } from '@/components/ui';

export interface BuybackFeedProps {
  /** Buyback transactions */
  buybacks: FormattedBuyback[] | null;
  /** Is data loading */
  isLoading?: boolean;
  /** Max items to show */
  limit?: number;
  /** Show pool total at bottom */
  showPoolTotal?: boolean;
  /** Pool balance (COPPER tokens) */
  poolBalance?: number;
  /** Pool USD value */
  poolValueUsd?: number;
  /** Additional class names */
  className?: string;
}

/**
 * BuybackFeed - Recent buyback transactions
 */
export function BuybackFeed({
  buybacks,
  isLoading = false,
  limit = 5,
  showPoolTotal = true,
  poolBalance,
  poolValueUsd,
  className,
}: BuybackFeedProps) {
  if (isLoading) {
    return <BuybackFeedSkeleton limit={limit} className={className} />;
  }

  const displayBuybacks = buybacks?.slice(0, limit) ?? [];

  return (
    <TerminalCard
      title="BUYBACK FEED"
      className={className}
      headerRight={
        <Badge variant="accent" size="sm">
          LIVE
        </Badge>
      }
    >
      <div className="space-y-2">
        {displayBuybacks.length > 0 ? (
          <>
            {displayBuybacks.map((buyback) => (
              <BuybackRow key={buyback.txSignature} buyback={buyback} />
            ))}

            {/* Pool Total */}
            {showPoolTotal && poolBalance !== undefined && (
              <div className="pt-2 mt-2 border-t border-zinc-800 lg:border-terminal-border">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-zinc-500 lg:font-mono lg:text-gray-500">
                    Pool Total
                  </span>
                  <div className="text-right">
                    <span className="font-medium text-white glow-white lg:font-mono">
                      {formatCompactNumber(poolBalance)} $COPPER
                    </span>
                    {poolValueUsd !== undefined && (
                      <span className="text-xs text-zinc-500 ml-2">
                        ({formatUSD(poolValueUsd)})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-6 text-zinc-500">
            <div className="text-2xl mb-2">📦</div>
            <p className="text-sm">No buybacks yet</p>
            <p className="text-xs text-zinc-600 mt-1">
              Buybacks occur when creator rewards arrive
            </p>
          </div>
        )}
      </div>
    </TerminalCard>
  );
}

/**
 * Single buyback row
 */
function BuybackRow({ buyback }: { buyback: FormattedBuyback }) {
  const solscanUrl = `https://solscan.io/tx/${buyback.txSignature}`;

  return (
    <a
      href={solscanUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'block px-3 py-2 -mx-1 rounded',
        'transition-colors hover:bg-zinc-800/50',
        'group'
      )}
    >
      {/* Desktop Layout */}
      <div className="hidden lg:flex items-center justify-between font-mono text-sm">
        <div className="flex items-center gap-3">
          <span className="text-gray-500">[{buyback.timeAgo}]</span>
          <span className="text-gray-400">{formatSOL(buyback.solAmount, 2)}</span>
          <span className="text-zinc-600">→</span>
          <span className="text-white">
            {formatCompactNumber(buyback.copperAmount)} $COPPER
          </span>
        </div>
        <span className="text-xs text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity">
          View TX ↗
        </span>
      </div>

      {/* Mobile Layout */}
      <div className="lg:hidden">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-white glow-white font-medium">
              +{formatCompactNumber(buyback.copperAmount)}
            </span>
            <span className="text-xs text-zinc-500">$COPPER</span>
          </div>
          <span className="text-xs text-zinc-500">{buyback.timeAgo}</span>
        </div>
        <div className="text-xs text-zinc-500 mt-0.5">
          from {formatSOL(buyback.solAmount, 2)}
        </div>
      </div>
    </a>
  );
}

/**
 * Loading skeleton
 */
function BuybackFeedSkeleton({
  limit = 5,
  className,
}: {
  limit?: number;
  className?: string;
}) {
  return (
    <TerminalCard title="BUYBACK FEED" className={className}>
      <div className="space-y-2">
        {Array.from({ length: limit }).map((_, i) => (
          <div key={i} className="px-3 py-2 -mx-1">
            {/* Desktop */}
            <div className="hidden lg:flex items-center gap-3">
              <Skeleton className="h-4 w-14" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4 w-24" />
            </div>
            {/* Mobile */}
            <div className="lg:hidden space-y-1">
              <div className="flex justify-between">
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-4 w-12" />
              </div>
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </div>
    </TerminalCard>
  );
}
