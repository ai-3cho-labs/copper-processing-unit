'use client';

import { useQuery } from '@tanstack/react-query';
import { getGlobalStats } from '@/lib/api';
import { DEFAULT_REFETCH_INTERVAL } from '@/lib/constants';
import type { GlobalStatsResponse } from '@/types/api';

/** Query key for global stats */
export const GLOBAL_STATS_QUERY_KEY = ['globalStats'] as const;

/**
 * Hook to fetch global statistics
 * Refetches every 60 seconds
 */
export function useGlobalStats() {
  return useQuery<GlobalStatsResponse, Error>({
    queryKey: GLOBAL_STATS_QUERY_KEY,
    queryFn: getGlobalStats,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: DEFAULT_REFETCH_INTERVAL, // 60 seconds
  });
}
