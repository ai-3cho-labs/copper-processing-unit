'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getBuybacks } from '@/lib/api';
import { formatTimeAgo } from '@/lib/utils';
import type { BuybackItem } from '@/types/api';
import type { FormattedBuyback } from '@/types/models';

/** Query key factory for buybacks */
export const buybacksQueryKey = (limit: number) =>
  ['buybacks', limit] as const;

/**
 * Transform buyback item to UI-friendly format
 */
function transformBuyback(item: BuybackItem): FormattedBuyback {
  const executedAt = new Date(item.executed_at);
  return {
    txSignature: item.tx_signature,
    solAmount: item.sol_amount,
    copperAmount: item.copper_amount,
    pricePerToken: item.price_per_token,
    executedAt,
    timeAgo: formatTimeAgo(executedAt),
  };
}

/**
 * Hook to fetch recent buybacks
 * @param limit - Number of buybacks to fetch (default: 10)
 */
export function useBuybacks(limit = 10) {
  const query = useQuery<BuybackItem[], Error>({
    queryKey: buybacksQueryKey(limit),
    queryFn: () => getBuybacks(limit),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
  });

  // Transform data for UI consumption
  const data = useMemo(() => {
    if (!query.data) return null;
    return query.data.map(transformBuyback);
  }, [query.data]);

  return {
    ...query,
    data,
    rawData: query.data,
  };
}
