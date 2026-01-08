'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getPoolStatus } from '@/lib/api';
import { POOL_REFETCH_INTERVAL } from '@/lib/constants';
import { DISTRIBUTION_THRESHOLD_USD } from '@/types/models';
import type { PoolStatusResponse } from '@/types/api';
import type { PoolInfo } from '@/types/models';

/** Query key for pool status */
export const POOL_STATUS_QUERY_KEY = ['poolStatus'] as const;

/**
 * Transform API response to UI-friendly model
 */
function transformPoolStatus(data: PoolStatusResponse): PoolInfo {
  return {
    balance: data.balance,
    balanceRaw: data.balance_raw,
    valueUsd: data.value_usd,
    lastPayout: data.last_distribution
      ? new Date(data.last_distribution)
      : null,
    hoursSinceLast: data.hours_since_last,
    hoursUntilTrigger: data.hours_until_time_trigger,
    progressToThreshold: Math.min(
      100,
      (data.value_usd / DISTRIBUTION_THRESHOLD_USD) * 100
    ),
    thresholdMet: data.threshold_met,
    timeTriggerMet: data.time_trigger_met,
    nextTrigger: data.next_trigger,
  };
}

/**
 * Hook to fetch airdrop pool status
 */
export function usePoolStatus() {
  const query = useQuery<PoolStatusResponse, Error>({
    queryKey: POOL_STATUS_QUERY_KEY,
    queryFn: getPoolStatus,
    staleTime: 15 * 1000, // 15 seconds
    refetchInterval: POOL_REFETCH_INTERVAL, // 30 seconds
  });

  // Transform data for UI consumption
  const data = useMemo(() => {
    if (!query.data) return null;
    return transformPoolStatus(query.data);
  }, [query.data]);

  return {
    ...query,
    data,
    rawData: query.data,
  };
}
