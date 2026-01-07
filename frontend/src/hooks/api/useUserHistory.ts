'use client';

import { useQuery } from '@tanstack/react-query';
import { getUserHistory } from '@/lib/api';
import type { DistributionHistoryItem } from '@/types/api';

/** Query key factory for user history */
export const userHistoryQueryKey = (wallet: string, limit: number) =>
  ['userHistory', wallet, limit] as const;

/**
 * Hook to fetch user distribution history
 * @param wallet - Wallet address
 * @param limit - Number of items to fetch (default: 10)
 */
export function useUserHistory(wallet: string | null, limit = 10) {
  return useQuery<DistributionHistoryItem[], Error>({
    queryKey: userHistoryQueryKey(wallet || '', limit),
    queryFn: () => getUserHistory(wallet!, limit),
    enabled: !!wallet,
    staleTime: 60 * 1000, // 1 minute
  });
}
