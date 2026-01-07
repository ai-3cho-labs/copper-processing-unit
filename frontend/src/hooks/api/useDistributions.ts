'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getDistributions } from '@/lib/api';
import { formatTimeAgo } from '@/lib/utils';
import type { DistributionItem } from '@/types/api';
import type { FormattedDistribution } from '@/types/models';

/** Query key factory for distributions */
export const distributionsQueryKey = (limit: number) =>
  ['distributions', limit] as const;

/**
 * Transform distribution item to UI-friendly format
 */
function transformDistribution(item: DistributionItem): FormattedDistribution {
  const executedAt = new Date(item.executed_at);
  return {
    id: item.id,
    poolAmount: item.pool_amount,
    poolValueUsd: item.pool_value_usd,
    totalHashpower: item.total_hashpower,
    recipientCount: item.recipient_count,
    triggerType: item.trigger_type,
    executedAt,
    timeAgo: formatTimeAgo(executedAt),
  };
}

/**
 * Hook to fetch recent distributions
 * @param limit - Number of distributions to fetch (default: 10)
 */
export function useDistributions(limit = 10) {
  const query = useQuery<DistributionItem[], Error>({
    queryKey: distributionsQueryKey(limit),
    queryFn: () => getDistributions(limit),
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  });

  // Transform data for UI consumption
  const data = useMemo(() => {
    if (!query.data) return null;
    return query.data.map(transformDistribution);
  }, [query.data]);

  return {
    ...query,
    data,
    rawData: query.data,
  };
}
